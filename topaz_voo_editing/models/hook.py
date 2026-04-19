from odoo.api import Environment, SUPERUSER_ID

def assign_group_to_all_users(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    group = env.ref('topaz_voo_editing.group_creative_push_notification')
    users = env['res.users'].search([])
    users.write({'groups_id': [(4, group.id)]})
