# -*- coding: utf-8 -*-
"""Payment Dashboard - read-only SQL views for Collector / Admin drill-down.

Two database views are exposed:

- ``bhu.payment.project.summary``  → consolidated per-project KPIs.
- ``bhu.payment.village.summary``  → per-project + per-village KPIs.

Both views aggregate from ``bhu.payment.reconciliation.bank.line`` joined with
``bhu.payment.reconciliation.bank`` so they stay in sync with bank reconciliation
activity, i.e. each settled / failed / pending bank transaction.
"""

from odoo import api, fields, models, tools


class PaymentProjectSummary(models.Model):
    _name = 'bhu.payment.project.summary'
    _description = 'Payment Dashboard - Project Summary'
    _auto = False
    _order = 'failed_count desc, project_name'

    project_id = fields.Many2one('bhu.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project', readonly=True)
    total_count = fields.Integer(string='Total Payments', readonly=True)
    success_count = fields.Integer(string='Successful', readonly=True)
    failed_count = fields.Integer(string='Failed', readonly=True)
    pending_count = fields.Integer(string='Pending', readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True)
    success_amount = fields.Float(string='Successful Amount', readonly=True)
    failed_amount = fields.Float(string='Failed Amount', readonly=True)
    pending_amount = fields.Float(string='Pending Amount', readonly=True)
    success_rate = fields.Float(string='Success Rate %', readonly=True, digits=(6, 2))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    recon.project_id AS id,
                    recon.project_id AS project_id,
                    proj.name AS project_name,
                    COUNT(line.id) AS total_count,
                    COUNT(line.id) FILTER (WHERE line.status = 'settled') AS success_count,
                    COUNT(line.id) FILTER (WHERE line.status = 'failed') AS failed_count,
                    COUNT(line.id) FILTER (WHERE line.status = 'pending') AS pending_count,
                    COALESCE(SUM(line.credit_amount), 0) AS total_amount,
                    COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'settled'), 0) AS success_amount,
                    COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'failed'), 0) AS failed_amount,
                    COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'pending'), 0) AS pending_amount,
                    CASE
                        WHEN COUNT(line.id) > 0
                        THEN (COUNT(line.id) FILTER (WHERE line.status = 'settled'))::float
                             / COUNT(line.id) * 100.0
                        ELSE 0
                    END AS success_rate
                FROM bhu_payment_reconciliation_bank_line line
                JOIN bhu_payment_reconciliation_bank recon ON recon.id = line.reconciliation_id
                LEFT JOIN bhu_project proj ON proj.id = recon.project_id
                WHERE recon.project_id IS NOT NULL
                GROUP BY recon.project_id, proj.name
            )
            """ % self._table
        )

    def action_open_villages(self):
        """Drill-down: open village-wise summary for this project."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Village Payment Summary - %s' % (self.project_name or ''),
            'res_model': 'bhu.payment.village.summary',
            'view_mode': 'kanban,list',
            'domain': [('project_id', '=', self.project_id.id)],
            'context': {'default_project_id': self.project_id.id},
            'target': 'current',
        }


class PaymentVillageSummary(models.Model):
    _name = 'bhu.payment.village.summary'
    _description = 'Payment Dashboard - Village Summary'
    _auto = False
    _order = 'failed_count desc, village_name'

    project_id = fields.Many2one('bhu.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project', readonly=True)
    village_id = fields.Many2one('bhu.village', string='Village', readonly=True)
    village_name = fields.Char(string='Village', readonly=True)
    total_count = fields.Integer(string='Total Payments', readonly=True)
    success_count = fields.Integer(string='Successful', readonly=True)
    failed_count = fields.Integer(string='Failed', readonly=True)
    pending_count = fields.Integer(string='Pending', readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True)
    success_amount = fields.Float(string='Successful Amount', readonly=True)
    failed_amount = fields.Float(string='Failed Amount', readonly=True)
    pending_amount = fields.Float(string='Pending Amount', readonly=True)
    success_rate = fields.Float(string='Success Rate %', readonly=True, digits=(6, 2))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    (recon.project_id * 1000000 + recon.village_id) AS id,
                    recon.project_id AS project_id,
                    proj.name AS project_name,
                    recon.village_id AS village_id,
                    vill.name AS village_name,
                    COUNT(line.id) AS total_count,
                    COUNT(line.id) FILTER (WHERE line.status = 'settled') AS success_count,
                    COUNT(line.id) FILTER (WHERE line.status = 'failed') AS failed_count,
                    COUNT(line.id) FILTER (WHERE line.status = 'pending') AS pending_count,
                    COALESCE(SUM(line.credit_amount), 0) AS total_amount,
                    COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'settled'), 0) AS success_amount,
                    COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'failed'), 0) AS failed_amount,
                    COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'pending'), 0) AS pending_amount,
                    CASE
                        WHEN COUNT(line.id) > 0
                        THEN (COUNT(line.id) FILTER (WHERE line.status = 'settled'))::float
                             / COUNT(line.id) * 100.0
                        ELSE 0
                    END AS success_rate
                FROM bhu_payment_reconciliation_bank_line line
                JOIN bhu_payment_reconciliation_bank recon ON recon.id = line.reconciliation_id
                LEFT JOIN bhu_project proj ON proj.id = recon.project_id
                LEFT JOIN bhu_village vill ON vill.id = recon.village_id
                WHERE recon.project_id IS NOT NULL AND recon.village_id IS NOT NULL
                GROUP BY recon.project_id, proj.name, recon.village_id, vill.name
            )
            """ % self._table
        )

    def action_open_failed_lines(self):
        """Drill-down: open failed payment lines for this village + project."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Failed Payments - %s / %s' % (self.project_name or '', self.village_name or ''),
            'res_model': 'bhu.payment.reconciliation.bank.line',
            'view_mode': 'list,form',
            'domain': [
                ('status', '=', 'failed'),
                ('reconciliation_id.project_id', '=', self.project_id.id),
                ('reconciliation_id.village_id', '=', self.village_id.id),
            ],
            'target': 'current',
        }


class PaymentDashboard(models.TransientModel):
    """Top banner record used by the Payment Dashboard view.

    Holds org-wide consolidated KPIs so we can render nice header cards
    alongside the per-project kanban.
    """
    _name = 'bhu.payment.dashboard'
    _description = 'Payment Dashboard (Consolidated)'

    total_count = fields.Integer(string='Total Payments', readonly=True)
    success_count = fields.Integer(string='Successful', readonly=True)
    failed_count = fields.Integer(string='Failed', readonly=True)
    pending_count = fields.Integer(string='Pending', readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True)
    success_amount = fields.Float(string='Successful Amount', readonly=True)
    failed_amount = fields.Float(string='Failed Amount', readonly=True)
    pending_amount = fields.Float(string='Pending Amount', readonly=True)
    success_rate = fields.Float(string='Success Rate %', readonly=True, digits=(6, 2))
    project_count = fields.Integer(string='Projects Tracked', readonly=True)
    village_count = fields.Integer(string='Villages Tracked', readonly=True)

    @api.model
    def _compute_consolidated(self):
        self.env.cr.execute(
            """
            SELECT
                COUNT(line.id) AS total_count,
                COUNT(line.id) FILTER (WHERE line.status = 'settled') AS success_count,
                COUNT(line.id) FILTER (WHERE line.status = 'failed') AS failed_count,
                COUNT(line.id) FILTER (WHERE line.status = 'pending') AS pending_count,
                COALESCE(SUM(line.credit_amount), 0) AS total_amount,
                COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'settled'), 0) AS success_amount,
                COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'failed'), 0) AS failed_amount,
                COALESCE(SUM(line.credit_amount) FILTER (WHERE line.status = 'pending'), 0) AS pending_amount,
                COUNT(DISTINCT recon.project_id) AS project_count,
                COUNT(DISTINCT recon.village_id) AS village_count
            FROM bhu_payment_reconciliation_bank_line line
            JOIN bhu_payment_reconciliation_bank recon ON recon.id = line.reconciliation_id
            """
        )
        row = self.env.cr.dictfetchone() or {}
        total = row.get('total_count') or 0
        success = row.get('success_count') or 0
        row['success_rate'] = (success / total * 100.0) if total else 0.0
        return row

    @api.model
    def action_open_dashboard(self):
        vals = self._compute_consolidated()
        record = self.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Dashboard',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': record.id,
            'target': 'current',
        }

    def action_open_all_projects(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Project Payment Summary',
            'res_model': 'bhu.payment.project.summary',
            'view_mode': 'kanban,list',
            'target': 'current',
        }

    def action_open_all_failed(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Failed Payments',
            'res_model': 'bhu.payment.reconciliation.bank.line',
            'view_mode': 'list,form',
            'domain': [('status', '=', 'failed')],
            'target': 'current',
        }

    def action_refresh(self):
        self.ensure_one()
        vals = self._compute_consolidated()
        self.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # ------------------------------------------------------------------
    # OWL Dashboard RPC
    # ------------------------------------------------------------------

    @api.model
    def get_payment_dashboard_data(self):
        """One-shot RPC that returns every KPI + table needed by the OWL
        payment dashboard component.

        Returns
        -------
        dict
            {
                'stats': { total/success/failed/pending counts + amounts + rate,
                            project_count, village_count },
                'projects': [ { id, name, total, success, failed, pending,
                                 total_amount, success_amount, failed_amount,
                                 pending_amount, success_rate } ],
                'villages': [ { project_id, project_name, village_id,
                                 village_name, ...counts + amounts } ],
                'recent_failures': [ { id, utr_number, beneficiary_name,
                                        credit_amount, error, project_name,
                                        village_name, reconciliation_id } ],
            }
        """
        stats = self._compute_consolidated()
        stats['success_rate'] = round(stats.get('success_rate') or 0.0, 2)

        payment_projects = self.env['bhu.payment.project.summary'].sudo().search_read(
            [], [
                'project_id', 'project_name',
                'total_count', 'success_count', 'failed_count', 'pending_count',
                'total_amount', 'success_amount', 'failed_amount', 'pending_amount',
                'success_rate',
            ], order='failed_count desc, project_name',
        )
        payment_by_project = {}
        for p in payment_projects:
            p['project_id'] = p['project_id'][0] if p.get('project_id') else False
            p['success_rate'] = round(p.get('success_rate') or 0.0, 2)
            if p['project_id']:
                payment_by_project[p['project_id']] = p

        # Include every project in the dashboard, even if it has zero payment
        # reconciliation records so the collector gets one complete view.
        all_projects = self.env['bhu.project'].sudo().search_read(
            [],
            ['name', 'code', 'state', 'department_id', 'district_id', 'village_ids', 'total_cost', 'create_date'],
            order='create_date desc, name',
        )
        unique_village_ids = set()
        for project in all_projects:
            unique_village_ids.update(project.get('village_ids') or [])
        stats['project_count'] = len(all_projects)
        stats['village_count'] = len(unique_village_ids)

        projects = []
        for project in all_projects:
            project_id = project['id']
            payment = payment_by_project.get(project_id, {})

            total_count = int(payment.get('total_count') or 0)
            success_count = int(payment.get('success_count') or 0)
            failed_count = int(payment.get('failed_count') or 0)
            pending_count = int(payment.get('pending_count') or 0)
            success_rate = round(payment.get('success_rate') or 0.0, 2)

            if total_count == 0:
                payment_status = 'No Payment'
                payment_status_key = 'none'
            elif failed_count > 0:
                payment_status = 'Needs Attention'
                payment_status_key = 'danger'
            elif pending_count > 0:
                payment_status = 'In Progress'
                payment_status_key = 'warning'
            else:
                payment_status = 'Healthy'
                payment_status_key = 'success'

            projects.append({
                'id': project_id,
                'project_id': project_id,
                'project_name': project.get('name') or '',
                'project_code': project.get('code') or '',
                'project_state': project.get('state') or '',
                'department_name': (
                    project.get('department_id')[1]
                    if project.get('department_id') and len(project.get('department_id')) > 1
                    else ''
                ),
                'district_name': (
                    project.get('district_id')[1]
                    if project.get('district_id') and len(project.get('district_id')) > 1
                    else ''
                ),
                'village_count': len(project.get('village_ids') or []),
                'total_cost': project.get('total_cost') or '',
                'total_count': total_count,
                'success_count': success_count,
                'failed_count': failed_count,
                'pending_count': pending_count,
                'total_amount': float(payment.get('total_amount') or 0.0),
                'success_amount': float(payment.get('success_amount') or 0.0),
                'failed_amount': float(payment.get('failed_amount') or 0.0),
                'pending_amount': float(payment.get('pending_amount') or 0.0),
                'success_rate': success_rate,
                'payment_status': payment_status,
                'payment_status_key': payment_status_key,
            })
        projects.sort(
            key=lambda row: (
                0 if row['payment_status_key'] == 'danger' else
                1 if row['payment_status_key'] == 'warning' else
                2 if row['payment_status_key'] == 'none' else
                3,
                (row.get('project_name') or '').lower(),
            )
        )

        villages = self.env['bhu.payment.village.summary'].sudo().search_read(
            [], [
                'project_id', 'project_name', 'village_id', 'village_name',
                'total_count', 'success_count', 'failed_count', 'pending_count',
                'total_amount', 'success_amount', 'failed_amount', 'pending_amount',
                'success_rate',
            ], order='project_name, failed_count desc, village_name',
        )
        for v in villages:
            v['project_id'] = v['project_id'][0] if v.get('project_id') else False
            v['village_id'] = v['village_id'][0] if v.get('village_id') else False
            v['success_rate'] = round(v.get('success_rate') or 0.0, 2)

        recent_failures = []
        failures = self.env['bhu.payment.reconciliation.bank.line'].sudo().search(
            [('status', '=', 'failed')], limit=15, order='id desc',
        )
        for f in failures:
            recon = f.reconciliation_id
            recent_failures.append({
                'id': f.id,
                'reconciliation_id': recon.id,
                'reconciliation_name': recon.name or '',
                'utr_number': f.utr_number or '',
                'beneficiary_name': f.beneficiary_name or '',
                'beneficiary_account': f.beneficiary_account or '',
                'credit_amount': f.credit_amount or 0.0,
                'error': (f.error or f.event_status or '')[:120],
                'project_name': recon.project_id.name or '',
                'village_name': recon.village_id.name or '',
            })

        return {
            'stats': stats,
            'projects': projects,
            'villages': villages,
            'recent_failures': recent_failures,
        }
