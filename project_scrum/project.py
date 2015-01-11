# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class projectProjectInehrit(models.Model):
    _inherit = 'project.project'

    @api.model
    def _get_stage_common(self):
        return self.env['project.scrum.pb.stage'].search([('case_default','=',1)])

    @api.model
    def _get_feature_common(self):
        return self.env['project.scrum.story.feature'].search([('case_default','=',1)])

    @api.one
    def _count_sandbox(self):
        self.sandbox_count = self.env['project.scrum.product.backlog'].search_count([('project_id', '=', self.id), ('stage_id.code','=','first')])
    
    @api.one
    def _count_story(self):
        self.story_count = self.env['project.scrum.product.backlog'].search_count([('project_id', '=', self.id), ('stage_id.code','!=','first')])

    @api.one
    def _count_sprint(self):
        self.sprint_count = len(self.sprint_ids)

    @api.one
    def _count_release(self):
        self.release_count = len(self.release_ids)

    release_count = fields.Integer(compute='_count_release', string='Count releases')
    sprint_count = fields.Integer(compute='_count_sprint', string='Count sprint')
    sandbox_count = fields.Integer(compute='_count_sandbox', string='Count sandbox stories')
    story_count = fields.Integer(compute='_count_story', string='Count accepted stories')
    sprint_ids = fields.One2many('project.scrum.sprint', 'project_id', 'Sprints', readonly=True)
    release_ids =  fields.One2many('project.scrum.release', 'project_id', "Releases", readonly=True)
    pb_feature_ids = fields.Many2many(comodel_name='project.scrum.story.feature', relation='project_scrum_story_feature_rel', column1='project_id', column2='feature_id', string='Story Features', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}, default=_get_feature_common)
    pb_stage_ids = fields.Many2many(comodel_name='project.scrum.pb.stage', relation='project_scrum_backlog_stage_rel', column1='project_id', column2='stage_id', string='Backlog Stages', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}, default=_get_stage_common)
    is_scrum =  fields.Boolean("Is it a Scrum Project ?", default=True)
    scrum_master_id = fields.Many2one('res.users', 'Scrum Master', help="The person who is maintains the processes for the product")
    product_owner_id =  fields.Many2one('res.users', "Product Owner")
    goal = fields.Text("Goal", help="The document that includes the project, jointly between the team and the customer")


