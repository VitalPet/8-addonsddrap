# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class projectScrumSandbox(models.Model):
    _name = 'project.scrum.sandbox'
    
    role_id = fields.Many2one('project.scrum.role', "As", required=True)
    name = fields.Char('I want', size=128, required=True)
    for_then = fields.Char('For', size=128, required=True)
    project_id = fields.Many2one('project.project', "Project", required=True, domain=[('is_scrum', '=', True)])
    developer_id = fields.Many2one('res.users', 'Developer')
    
    _defaults = {
        'developer_id': lambda self, cr, uid, context: uid,
    }
