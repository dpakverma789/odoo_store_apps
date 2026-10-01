"""Independent-process PostgreSQL check; run only against a disposable codex_* DB.

python check_concurrency.py --odoo-root /path/to/odoo --config /path/to/odoo.conf 
    --database codex_session_pro_test

Not imported by Odoo's transactional test runner: real commits and distinct
processes are necessary to test REPEATABLE READ and multiple worker registries.
"""
import argparse
import multiprocessing
import sys
from uuid import uuid4


def registry(options):
    sys.path.insert(0, options.odoo_root)
    import odoo
    from odoo.tools import config
    from odoo.modules.registry import Registry
    config.parse_config(["-c", options.config, "-d", options.database, "--no-http"])
    return odoo, Registry(options.database)


def worker(options, user_id, barrier, output):
    try:
        odoo, reg = registry(options)
        from odoo.service.model import retrying
        with reg.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            attempts = 0
            def attempt():
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    # Both workers start from the same pre-login snapshot.
                    cr.execute("SELECT session_policy_revision FROM res_users WHERE id = %s", [user_id])
                    barrier.wait(timeout=30)
                row = env["user.session"]._register_session(env["res.users"].browse(user_id), uuid4().hex)
                return row.id
            row_id = retrying(attempt, env)
            output.put(("ok", row_id, attempts))
    except Exception as exc:
        output.put(("error", type(exc).__name__, str(exc)))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--odoo-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--database", required=True)
    options = parser.parse_args()
    if not options.database.startswith("codex_"):
        parser.error("Use a disposable codex_* database; this check commits fixtures.")
    odoo, reg = registry(options)
    context = multiprocessing.get_context("spawn")
    for policy in ["replace_existing", "reject_new"]:
        with reg.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            params = env["ir.config_parameter"]
            key = "single_session_login_pro.conflict_policy"
            previous = params.get_param(key, "replace_existing")
            params.set_param(key, policy)
            user = env["res.users"].create({"name": "Concurrency fixture", "login": "codex-race-" + uuid4().hex})
            user_id = user.id
            cr.commit()
        try:
            barrier, output = context.Barrier(2), context.Queue()
            processes = [context.Process(target=worker, args=(options, user_id, barrier, output)) for _ in range(2)]
            for process in processes:
                process.start()
            results = [output.get(timeout=60) for _ in processes]
            for process in processes:
                process.join(timeout=30)
                assert process.exitcode == 0, results
            assert all(result[0] == "ok" for result in results), results
            assert sum(result[2] for result in results) >= 3, "Expected at least one serialization retry"
            with reg.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                rows = env["user.session"].with_context(active_test=False).search([("user_id", "=", user_id)])
                assert len(rows) == 2
                assert len(rows.filtered(lambda row: row.status == "active")) == 1
                reason = "replaced_by_new_login" if policy == "replace_existing" else "new_login_rejected"
                assert len(rows.filtered(lambda row: row.end_reason == reason)) == 1
            print(f"PASS {policy}: two processes, one active session, database retry observed", flush=True)
        finally:
            with reg.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                env["res.users"].browse(user_id).unlink()
                env["ir.config_parameter"].set_param(key, previous)
                cr.commit()


if __name__ == "__main__":
    main()
