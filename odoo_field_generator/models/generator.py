from odoo import models, fields

ODOO_DATA_TYPE = {
    'c': 'Char',
    'i': 'Integer',
    'f': 'Float',
    'd': 'Date',
    'dt': 'Datetime',
    'bi': 'Binary',
    's': 'Selection',
    'b': 'Boolean',
    'mo': 'Many2one',
    'om': 'One2many',
    'mm': 'Many2many'
}


class OdooFieldGenerator(models.Model):
    _name = "odoo.field.generator"
    _description = "Odoo Field Syntax Generator"
    _rec_name = 'id'

    variable_input = fields.Text(string="Variable", required=True, help="Example:\nname.c\nage.i\nsalary.f")
    python_output = fields.Text(string="Python Fields", readonly=True)
    xml_output = fields.Text(string="XML Fields", readonly=True)

    def _generate_field(self, variable):
        """Generate Python and XML syntax for one variable"""

        variable_name, variable_type = variable.split(".")
        label = " ".join(variable_name.split("_")).title()

        # Adjust field name
        if variable_type == "mo":
            variable_name = f"{variable_name}_id"
        elif variable_type in ("om", "mm"):
            variable_name = f"{variable_name}_ids"

        base = f"{variable_name} = fields.{ODOO_DATA_TYPE[variable_type]}"

        # Python syntax
        python_formats = {
            "mo": f"{base}(comodel_name='your.model_name', string='{label}')",
            "om": f"{base}(comodel_name='your.model_name', inverse_name='', string='{label}')",
            "mm": f"{base}(comodel_name='your.model_name', 'table_rel', 'col1_id', 'col2_id', string='{label}')",
            "s": f"{base}([('option_1','Option 1'),('option_2','Option 2')], string='{label}', default='option_1')"
        }

        py_line = python_formats.get(variable_type, f"{base}(string='{label}')")

        # XML syntax
        xml_line = f'<field name="{variable_name}"/>'

        if variable_type == "mm":
            xml_line = f'<field name="{variable_name}" widget="many2many_tags"/>'
        if variable_type == "bi":
            xml_line = f'<field name="{variable_name}" widget="image" class="oe_avatar"/>'
        if variable_type == "b":
            xml_line = f'<field name="{variable_name}" widget="boolean_toggle"/>'

        return py_line, xml_line

    def action_generate(self):
        """Generate Python and XML syntax"""

        for rec in self:
            variables = [v.strip("', ") for v in rec.variable_input.splitlines() if v.strip()]
            py_lines = []
            xml_lines = []
            for variable in variables:
                py_line, xml_line = rec._generate_field(variable)
                py_lines.append(py_line)
                xml_lines.append(xml_line)

            rec.python_output = "\n".join(py_lines)
            rec.xml_output = "\n".join(xml_lines)