# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class projectScrumRelease(models.Model):
    _name = 'project.scrum.release'


    @api.model
    def _get_default_product_owner_id(self):
        return self.project_id.product_owner_id

    @api.model
    def _get_default_scrum_master_id(self):
        return self.project_id.scrum_master_id

    @api.onchange('project_id')
    def _onchange_project(self):
        if self.project_id:
            self.product_owner_id = self.project_id.product_owner_id
            self.scrum_master_id = self.project_id.scrum_master_id

    name = fields.Char("Name", size=128, required=True)
    goal = fields.Text("Goal")
    note =  fields.Text("Note")
    project_id = fields.Many2one('project.project', "Project", domain=[('is_scrum', '=', True)], required=True)
    sprint_ids = fields.One2many('project.scrum.sprint', 'release_id', "Sprints", readonly=True)

    # product_owner and scrum_master are inheriterd from project but can be change on specific release for big project.
    product_owner_id = fields.Many2one('res.users', 'Product Owner', default=_get_default_product_owner_id, required=True, help="The person who is responsible for the product")
    scrum_master_id = fields.Many2one('res.users', 'Scrum Master',  default=_get_default_scrum_master_id, required=True, help="The person who is maintains the processes for the product")
    date_start =  fields.Date('Starting Date')
    date_stop = fields.Date('Ending Date')
    delivery_date_estimated = fields.Date("Estimated date of delivery")
    delivery_date_effective = fields.Date("Effective date of delivery")

class projectProjectInehrit(models.Model):

    _inherit = 'project.project'

    release_ids =  fields.One2many('project.scrum.release', 'project_id', "Releases", readonly=True)
