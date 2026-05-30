import base64
import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    optimus_company_id = fields.Char(
        string='eZee Optimus Company ID',
        config_parameter='ezee_optimus.company_id'
    )
    optimus_auth_code = fields.Char(
        string='eZee Optimus Auth Code',
        config_parameter='ezee_optimus.auth_code'
    )
    optimus_base_url = fields.Char(
        string='eZee Optimus API URL',
        default='https://app.ipos247.com/app/cloudPOS/sl/interfaceapi/index.php/xeroaccountinterface/eoaccounts',
        config_parameter='ezee_optimus.base_url'
    )

    def _get_optimus_connection(self):
        ICP = self.env['ir.config_parameter'].sudo()
        company_id = (ICP.get_param('ezee_optimus.company_id') or '').strip()
        auth_code = (ICP.get_param('ezee_optimus.auth_code') or '').strip()
        base_url = (ICP.get_param(
            'ezee_optimus.base_url',
            'https://app.ipos247.com/app/cloudPOS/sl/interfaceapi/index.php/xeroaccountinterface/eoaccounts'
        ) or '').strip()

        _logger.info('eZee Optimus | company_id: "%s" | auth_code: "%s..." | url: "%s"',
                     company_id, auth_code[:10] if auth_code else '', base_url)

        if not all([company_id, auth_code, base_url]):
            raise UserError(
                'eZee Optimus credentials are not configured. '
                'Go to Accounting > Configuration > Settings and fill Company ID and Auth Code.'
            )

        headers = {'Content-Type': 'application/json'}
        return base_url, company_id, auth_code, headers