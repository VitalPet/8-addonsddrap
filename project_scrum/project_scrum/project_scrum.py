# -*- coding: utf-8 -*-
from datetime import datetime, date
import time
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

import re
from dateutil.relativedelta import relativedelta
from dateutil import parser

SPRINT_STATES = [('draft','Draft'),
    ('open','Open'),
    ('pending','Pending'),
    ('cancel','Cancelled'),
    ('done','Done')]

BACKLOG_STATES = [('draft','Draft'),
    ('open','Open'),
    ('pending','Pending'),
    ('done','Done'),
    ('cancel','Cancelled')]

class projectScrumSprint(models.Model):
    _name = 'project.scrum.sprint'
    _description = 'Project Scrum Sprint'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _track = {
        'state': {
            'project.mt_backlog_state': lambda self, cr, uid, obj, ctx=None: obj.state,
        },
    }

    @api.multi
    def name_get(self):
        result = []
        for sprint in self:
            date_start = parser.parse(sprint.date_start)
            date_stop = parser.parse( sprint.date_stop)
            result.append((sprint.id, "%s (%s-%s)" % (sprint.name, date_start.strftime('%d/%m') or '', date_stop.strftime('%d/%m') or '')))
        return result


    @api.multi
    @api.depends('progress','effective_hours','expected_hours')
    def _compute(self):
        for sprint in self:
            tot = 0.0
            prog = 0.0
            effective = 0.0
            progress = 0.0
            for bl in sprint.product_backlog_ids:
                tot += bl.expected_hours
                effective += bl.effective_hours
                prog += bl.expected_hours * bl.progress / 100.0
            if tot>0:
                progress = round(prog/tot*100)
            sprint['progress'] = progress
            sprint['expected_hours'] = tot
            sprint['effective_hours'] = effective

    @api.one
    def button_cancel(self):
        self.state = 'cancel'

    @api.one
    def button_draft(self):
        self.state = 'draft'

    @api.model
    def _verify_if_user_stories_in(self):
        story_ids = self.product_backlog_ids
        return len(story_ids) > 0

    @api.one
    def button_open(self):
        res = self._verify_if_user_stories_in()
        one_sprint_open = self._check_only_one_open()

        if not one_sprint_open:
            raise except_orm(_('Warning!'), _("You can not open sprint if one is already open for the same project and the same release"))
        if not res:
            raise except_orm(_('Warning!'), _("You can not open sprint with no stories affected in"))
        else:
            self.state = 'open'
            #FIX log() is deprecated, user OpenChatter instead
            #message = _("The sprint '%s' has been opened.") % (name,)

    @api.model
    def _get_velocity_sprint_done(self):
        velocity = 0
        for story_id in self.product_backlog_ids:
            velocity += story_id.complexity
        return velocity

    @api.one
    def button_close(self):
        effective_velocity = 0
        self.write({'state':'done', 'effective_velocity_sprint_done': self._get_velocity_sprint_done()})
        #TODO: implement message / log with openchatter -> message = _("The sprint '%s' has been closed.") % (self.name,)

    @api.one
    def button_pending(self):
        self.state = 'pending'

    @api.one
    def _get_velocity(self):
        self.effective_velocity = 0
        if self.product_backlog_ids:
            for story in self.product_backlog_ids:
                self.effective_velocity += story.complexity

    @api.onchange('release_id')
    def _onchange_release_id(self):
        if self.release_id:
            self.product_owner_id = self.release_id.product_owner_id
            self.scrum_master_id = self.release_id.scrum_master_id

    name =  fields.Char('Sprint Name', required=True, size=64)
    date_start = fields.Date('Starting Date', default=lambda self: fields.Date.today(self), required=True)
    date_stop = fields.Date('Ending Date', required=True)
    release_id = fields.Many2one('project.scrum.release', string='Release', domain="[('project_id','=', project_id)]", required=True)
    project_id = fields.Many2one('project.project', string='Project')
    product_backlog_ids = fields.One2many(comodel_name='project.scrum.product.backlog', inverse_name='sprint_id', string='User Stories')

    product_owner_id = fields.Many2one('res.users', string='Product Owner', required=True, help="The person who is responsible for the product")
    scrum_master_id = fields.Many2one('res.users', string='Scrum Master', required=True, help="The person who is maintains the processes for the product")

    task_ids = fields.One2many(comodel_name='project.task', inverse_name='sprint_id', string='Tasks')
    meeting_ids = fields.One2many(comodel_name='project.scrum.meeting', inverse_name='sprint_id', string='Daily Scrum')
    review = fields.Text('Sprint Review')

    retrospective_start_to_do = fields.Text('Start to do')
    retrospective_continue_to_do = fields.Text('Continue to do')
    retrospective_stop_to_do = fields.Text('Stop to do')

    backlog_ids = fields.One2many(comodel_name='project.scrum.product.backlog', inverse_name='sprint_id', string='Sprint Backlog')
    progress = fields.Float(compute='_compute', group_operator="avg", multi="progress", string='Progress (0-100)', help="Computed as: Time Spent / Total Time.")
    effective_hours =  fields.Float(compute='_compute', multi="effective_hours", string='Effective hours', help="Computed using the sum of the task work done.")
    expected_hours = fields.Float(compute='_compute', multi="expected_hours", string='Planned Hours', help='Estimated time to do the task.')
    state = fields.Selection(selection=SPRINT_STATES, string='State', default='draft', required=True)
    goal = fields.Char("Goal", size=128)

    planned_velocity = fields.Integer("Planned velocity", help="Estimated velocity for sprint, usually set by the development team during sprint planning.")
    effective_velocity = fields.Integer(compute='_get_velocity', string="Effective velocity", help="Computed using the sum of the task work done.")
    effective_velocity_sprint_done = fields.Integer("Effective velocity")

    _order = 'date_start desc'

    @api.one
    @api.constrains('date_start','date_stop')
    def _check_dates(self):
        if self.date_start > self.date_stop:
            raise Warning(_('Error! sprint start-date must be lower than project end-date.'))

    @api.model
    def _check_only_one_open(self):
        # Only one sprint can be open byt project_id/release_id
        opened_sprint_ids = self.search_count([('project_id', '=', self.project_id.id),('state','=','open'),('release_id','=', self.release_id.id)])
	if opened_sprint_ids > 0:
            return False
	return True

class projectScrumMeeting(models.Model):
    _name = 'project.scrum.meeting'
    _description = 'Scrum Meeting'

    name = fields.Char('Meeting Name', size=64)
    date = fields.Date('Meeting Date', default=lambda self: fields.Date.today(self), required=True)
    user_id = fields.Many2one('res.users', "Developer", default=lambda self: self.env.user, readonly=True)
    sprint_id = fields.Many2one('project.scrum.sprint', string='Sprint')
    project_id = fields.Many2one(related='sprint_id.release_id.project_id', string='Project', readonly=True)
    scrum_master_id = fields.Many2one(related='sprint_id.scrum_master_id', string='Scrum Master', readonly=True)
    product_owner_id = fields.Many2one(related='sprint_id.product_owner_id', string='Product Owner', readonly=True)
    question_yesterday = fields.Text('Tasks since yesterday')
    question_today = fields.Text('Tasks for today')
    question_blocks = fields.Text('Blocks encountered')
    task_ids = fields.Many2many(comodel_name='project.task', relation='project_scrum_meeting_task_rel', column1='meeting_id', column2='task_id', string='Tasks')
    user_story_ids = fields.Many2many(comodel_name='project.scrum.product.backlog', relation='project_scrum_meeting_story_rel', column1='meeting_id', column2='story_id', string='Stories')

    _order = 'date desc'

     #TODO: email with email template

class projectScrumPBStage(models.Model):
    """ Category of Product Backlog """
    _name = "project.scrum.pb.stage"
    _description = "Product Backlog Stage"


    #@api.model
    #def _get_default_project_ids(self):
    #    project_id = self.pool['project.scrum.product.backlog']._get_default_project_id(cr, uid, context=ctx)
    #    if project_id:
    #        return [project_id]
    #    return None

    name = fields.Char('Stage Name', translate=True, required=True)
    sequence = fields.Integer('Sequence', help="Used to order the story stages", default=1)
    user_id = fields.Many2one('res.users', string='Owner', help="Owner of the note stage.", default=lambda self: self.env.user, required=True)
    #FIX: think we should remove this
    project_id = fields.Many2one('project.project', string='Project', help="Project of the story stage.", required=False)
    case_default = fields.Boolean('Default for New Projects',
                        help="If you check this field, this stage will be proposed by default on each new project. It will not assign this stage to existing projects.")
    project_ids = fields.Many2many(comodel_name='project.project', relation='project_scrum_backlog_stage_rel', column1='stage_id', column2='project_id', string='Projects')
    fold = fields.Boolean('Folded by Default', default=0)
    code = fields.Char('Code', translate=False)
    _order = 'sequence asc'

class projectScrumBacklogFeature(models.Model):
    """ Feature associated to the stories """
    _name = "project.scrum.story.feature"
    _description = "Story Feature"

    name = fields.Char('Feature Name', translate=True, required=True)
    sequence = fields.Integer('Sequence', help="Used to order the story features", default=1)
    user_id = fields.Many2one('res.users', string='Owner', help="Owner of the story feature.", default=lambda self: self.env.user, required=True)
    case_default = fields.Boolean('Default for New Projects',
                        help="If you check this field, this Feature will be proposed by default on each new project. It will not assign this feature to existing projects.")
    project_ids = fields.Many2many(comodel_name='project.project', relation='project_scrum_story_feature_rel', column1='feature_id', column2='project_id', string='Projects')
    fold = fields.Boolean('Folded by Default', default=0)
    code = fields.Char('Code', translate=False)
    _order = 'sequence asc'


class projectScrumProductBacklog(models.Model):
    _name = 'project.scrum.product.backlog'
    _description = "Product backlog where are user stories"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _track = {
        'feature_id': {
            # this is only an heuristics; depending on your particular stage configuration it may not match all 'new' stages
            'project.mt_backlog_new': lambda self, cr, uid, obj, ctx=None: obj.feature_id and obj.feature_id.sequence <= 1,
            'project.mt_backlog_stage': lambda self, cr, uid, obj, ctx=None: obj.feature_id.sequence > 1,
        },
        'stage_id': {
            # this is only an heuristics; depending on your particular stage configuration it may not match all 'new' stages
            'project.mt_backlog_new': lambda self, cr, uid, obj, ctx=None: obj.stage_id and obj.stage_id.sequence <= 1,
            'project.mt_backlog_stage': lambda self, cr, uid, obj, ctx=None: obj.stage_id.sequence > 1,
        },
    }

    #@api.model
    #def _get_default_project_id(self):
    #    """ Gives default section by checking if present in the context """
    #    self._resolve_project_id_from_context()

    #@api.model
    #def _resolve_project_id_from_context(self):
    #    """ Returns ID of project based on the value of 'default_project_id'
    #        context key, or None if it cannot be resolved to a single
    #        project.
    #    """
    #    if context is None:
    #        context = {}
    #    if type(context.get('default_project_id')) in (int, long):
    #        return context['default_project_id']
    #    if isinstance(context.get('default_project_id'), basestring):
    #        project_name = context['default_project_id']
    #        project_ids = self.pool.get('project.project').name_search(cr, uid, name=project_name, context=context)
    #        if len(project_ids) == 1:
    #            return project_ids[0][0]
    #    return None

    @api.model
    def _get_sandbox_stage(self):
        first_stage = self.env['project.scrum.pb.stage'].search([('code','=','first'),('project_ids','in',self.project_id.id)])
        return first_stage and first_stage[0]

    @api.multi
    @api.depends('progress', 'effective_hours', 'task_hours')
    def _compute(self):
        for backlog in self:
            tot = 0.0
            prog = 0.0
            effective = 0.0
            task_hours = 0.0
            progress = 0.0
            if self.tasks_id:
                for task in self.tasks_id:
                    task_hours += task.total_hours
                    effective += task.effective_hours
                    tot += task.planned_hours
                    prog += task.planned_hours * task.progress / 100.0

            if tot > 0:
                progress = round(prog/tot*100)

            backlog['effective_hours'] = effective
            backlog['progress'] = progress
            backlog['task_hours'] = task_hours

    @api.one
    def button_cancel(self):
        self.write({'state': 'cancel', 'active': False})
        for task in self.tasks_id:
            task.state = 'cancelled'

    @api.one
    def button_draft(self):
        self.state = 'draft'

    @api.one
    def button_open(self):
        if not self.sprint_id:
            raise osv.except_osv(_("Warning !"), _("You must affect this user story in a sprint before open it."))
        elif not self.acceptance_testing:
            raise osv.except_osv(_("Warning !"), _("You must define acceptance testing before open this user story"))
        else:
            self.write({'state': 'open', 'date_open': fields.Date.today()})

    @api.one
    def button_close(self):
        self.write({'state': 'done', 'active': False,
                    'date_done': fields.Date.today()})
        for task in self.tasks_id:
            task.state = 'done'

    @api.one
    def tasks_done(self):
        if self.task_count == self.task_count_done:
            stage_id = self.env['project.scrum.pb.stage'].search([('code', '=', 'review'),('project_ids','in',self.project_id.id)])
            if stage_id:
                self.stage_id = stage_id
        else:
            if self.stage_id and self.stage_id.code in ['review','done']:
                stage_id = self.env['project.scrum.pb.stage'].search([('code', '=', 'pending'),('project_ids','in',self.project_id.id)])
                if stage_id:
                    self.stage_id = stage_id

    @api.one
    def set_pending(self):
        stage_id = self.env['project.scrum.pb.stage'].search([('code', '=', 'pending'),('project_ids','in',self.project_id.id)])
        if stage_id:
            self.stage_id = stage_id
        self.state = 'pending'

    @api.one
    def button_pending(self):
        self.state = 'pending'

    @api.multi
    def button_validate(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.stage_id = self.env['project.scrum.pb.stage'].search([('code', '=', 'validate'),('project_ids','in',self.project_id.id)])
        self.state = 'open'
        res = self.env.ref('project_scrum.action_project_scrum_product_sandbox_all')
        form_view = self.env.ref('project_scrum.view_project_scrum_product_backlog_form')
        ctx = self.env.context.copy()
        return {
            'name': "Complete Story Details",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': res.res_model,
            'views': [(form_view.id,'form')],
            'view_id': form_view.id,
            'target': 'current_edit',
            'context': ctx,
        }

    @api.multi
    def button_refuse(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.state = 'cancel'
        self.stage_id = self.env['project.scrum.pb.stage'].search([('code', '=', 'cancel'),('project_ids','in',self.project_id.id)])
        res = self.env.ref('project_scrum.action_project_scrum_product_sandbox_all')
        ctx = self.env.context.copy()
        return {
            'name': "Sandbox",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': res.res_model,
            'views': False,
            'view_id': False,
            'context': ctx,
            'domain': [('project_id','=',self.project_id.id),('stage_id.code','=','first')],
        }

    @api.one
    def _count_tasks(self):
        self.task_count = len(self.tasks_id)

    @api.one
    def _count_tasks_done(self):
        tasks_done = [task for task in self.tasks_id if task.stage_id and task.stage_id.code == 'done']
        self.task_count_done = len(tasks_done)

    task_count = fields.Integer(compute='_count_tasks', string='Count tasks')
    task_count_done = fields.Integer(compute='_count_tasks_done', string='Count tasks Done')
    priority =  fields.Selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority', select=True, default='1')
    role_id = fields.Many2one('project.scrum.role', string="As", readonly=True, states={'draft':[('readonly',False)]})
    name = fields.Char('Name', size=128, required=True, readonly=False)
    for_then = fields.Char('For', size=128, readonly=True, states={'draft':[('readonly',False)]})
    acceptance_testing = fields.Text("Acceptance testing", readonly=True, states={'draft':[('readonly',False)]})

    description = fields.Text("Description", default='En tant que: \nJe veux: \nPour: \n')
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of product backlog.", default=1000)
    expected_hours =  fields.Float('Planned Hours', help='Estimated total time to do the Backlog')
    complexity = fields.Integer('Complexity', help='Complexity of the User Story')
    active = fields.Boolean('Active', help="If Active field is set to true, it will allow you to hide the product backlog without removing it.", default=1)
    value_to_user = fields.Integer("Value to user", default=50)

    state = fields.Selection(selection=BACKLOG_STATES, string='State', required=True, default='draft')
    feature_id = fields.Many2one('project.scrum.story.feature', string='Feature', track_visibility='onchange', select=True,
                        domain="[('project_ids', 'in', project_id)]", copy=False)
    stage_id = fields.Many2one('project.scrum.pb.stage', string='Stage', track_visibility='onchange', select=True,
                        domain="[('project_ids', '=', project_id)]", copy=False, default=_get_sandbox_stage)
    open = fields.Boolean('Active', track_visibility='onchange', default=1)
    date_open = fields.Date("Date open")
    date_done = fields.Date("Date done")

    project_id = fields.Many2one('project.project', string="Project", required=True, readonly=True, states={'draft':[('readonly',False)]})
    release_id = fields.Many2one('project.scrum.release', string="Release", readonly=True, states={'draft':[('readonly',False)]})
    sprint_id = fields.Many2one('project.scrum.sprint', string="Sprint", readonly=True, states={'draft':[('readonly',False)]})

    user_id = fields.Many2one('res.users', string='Author', default=lambda self: self.env.user)
    task_id = fields.Many2one('project.task', required=False,
            string="Related Task", ondelete='restrict',
            help='Task-related data of the user story')
    tasks_id = fields.One2many(comodel_name='project.task', inverse_name='product_backlog_id', string='Tasks Details')

    progress = fields.Float(compute='_compute', multi='progress', group_operator='avg', string='Progress', help="Computed as: Time Spent / Total Time.")
    effective_hours = fields.Float(compute='_compute', multi="effective_hours", string='Spent Hours', help="Computed using the sum of the time spent on every related tasks", store=True)
    task_hours = fields.Float(compute='_compute', multi="task_hours", string='Task Hours', help='Estimated time of the total hours of the tasks')

    color = fields.Integer('Color Index')

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None,
                              access_rights_uid=None, context=None):
        search_domain = []
        project_id = self._context.get('default_project_id', False)
        if project_id:
            search_domain = [('project_ids', 'in', [project_id])]
        used_stages = self.env['project.scrum.pb.stage'].search(search_domain)
        result = used_stages.name_get()
        fold = {}
        for stage in used_stages:
            fold[stage.id] = stage.fold or False
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids,
    }

    _order = "priority desc, id asc"


class projectTaskInherit(models.Model):
    _inherit = 'project.task'


    @api.model
    def _get_backlog_sprint(self):
        if self.product_backlog_id:
            return self.product_backlog_id.id
        return False

    @api.onchange('product_backlog_id')
    def _onchange_backlog_id(self):
        if self.product_backlog_id:
            self.sprint_id  = self.product_backlog_id.sprint_id

    product_backlog_id = fields.Many2one('project.scrum.product.backlog', string='Product Backlog',
                help="Related product backlog that contains this task. Used in SCRUM methodology")
    sprint_id = fields.Many2one('project.scrum.sprint', string='Sprint', default=_get_backlog_sprint)
    release_id = fields.Many2one('project.scrum.release', related='sprint_id.release_id', string='Release', store=True)

    @api.multi
    def write(self, values):
        res = super(projectTaskInherit, self).write(values)
        if values.get('stage_id', False):
            new_stage = self.env['project.task.type'].browse([values['stage_id']])
            if self.product_backlog_id and (new_stage.code in ['pending']):
                self.product_backlog_id.stage_id = self.env['project.scrum.pb.stage'].search([('code', '=', 'pending')])
            if new_stage.code == 'done' and self.product_backlog_id:
                self.product_backlog_id.tasks_done()
            if new_stage.code not in ['done', 'cancelled'] \
               and self.product_backlog_id \
               and self.product_backlog_id.stage_id.code == 'review':
                self.product_backlog_id.set_pending()
        return res


class projectTaskTypeInherit(models.Model):
    _inherit = 'project.task.type'

    code = fields.Char('Code', translate=False)
