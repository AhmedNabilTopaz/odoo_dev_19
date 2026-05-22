from odoo import fields, models
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # eZee Optimus POS credentials
    optimus_hotel_code = fields.Char(
        string='eZee Optimus Hotel Code',
        config_parameter='ezee_optimus.hotel_code'
    )
    optimus_username = fields.Char(
        string='eZee Optimus Username',
        config_parameter='ezee_optimus.username'
    )
    optimus_password = fields.Char(
        string='eZee Optimus Password',
        config_parameter='ezee_optimus.password'
    )
    optimus_base_url = fields.Char(
        string='eZee Optimus Base URL',
        default='https://api.ipos247.com/v1/fas/',
        config_parameter='ezee_optimus.base_url'
    )

    def _get_optimus_connection(self):
        """Returns (base_url, hotel_code, headers) tuple for API calls."""
        ICP = self.env['ir.config_parameter'].sudo()
        hotel_code = (ICP.get_param('ezee_optimus.hotel_code') or '').strip()
        username = (ICP.get_param('ezee_optimus.username') or '').strip()
        password = (ICP.get_param('ezee_optimus.password') or '').strip()
        base_url = ICP.get_param('ezee_optimus.base_url',
                                 'https://api.ipos247.com/v1/fas/')
        base_url = (base_url or '').strip()

        if not all([hotel_code, username, password]):
            raise UserError(
                'eZee Optimus credentials are not configured. '
                'Go to Accounting > Configuration > Settings and fill Hotel Code, Username, and Password.'
            )

        headers = {
            'Content-Type': 'application/json',
        }
        auth = (username, password)
        return base_url, hotel_code, headers, auth
