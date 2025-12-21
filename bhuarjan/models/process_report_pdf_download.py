# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import io
import base64
import logging
import zipfile
from datetime import datetime

_logger = logging.getLogger(__name__)


class ProcessReportPdfDownload(models.AbstractModel):
    """Mixin for PDF download functionality in Process Report Wizard"""
    _name = 'bhu.process.report.pdf.download.mixin'
    _description = 'Process Report PDF Download Mixin'

    def action_download_all_pdfs(self):
        """Download all PDF reports as a zip file"""
        self.ensure_one()
        
        records = self._get_filtered_records()
        
        # Create zip file in memory
        zip_buffer = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
        
        pdf_count = 0
        
        try:
            # Generate Section 4 PDFs
            for record in records['section4']:
                try:
                    # Create wizard for Section 4
                    wizard = self.env['bhu.section4.notification.wizard'].create({
                        'project_id': record.project_id.id,
                        'village_id': record.village_id.id,
                        'public_purpose': record.public_purpose,
                        'public_hearing_datetime': record.public_hearing_datetime,
                        'public_hearing_place': record.public_hearing_place,
                        'directly_affected': record.directly_affected,
                        'indirectly_affected': record.indirectly_affected,
                        'private_assets': record.private_assets,
                        'government_assets': record.government_assets,
                        'minimal_acquisition': record.minimal_acquisition,
                        'alternatives_considered': record.alternatives_considered,
                        'total_cost': record.total_cost,
                        'project_benefits': record.project_benefits,
                        'compensation_measures': record.compensation_measures,
                        'other_components': record.other_components,
                    })
                    
                    # Generate PDF
                    report_action = self.env.ref('bhuarjan.action_report_section4_notification')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name, 
                        [wizard.id], 
                        data={}
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (record.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_')
                            village_name = (record.village_id.name or 'Unknown').replace('/', '_').replace('\\', '_')
                            filename = f'Section4_{project_name}_{village_name}_{record.name or record.id}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating PDF for Section 4 record {record.id}: {str(e)}", exc_info=True)
                    continue
            
            # Generate Section 11 PDFs
            for record in records['section11']:
                try:
                    report_action = self.env.ref('bhuarjan.action_report_section11_preliminary')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name,
                        [record.id],
                        data={}
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (record.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if record.project_id else 'Unknown'
                            village_name = (record.village_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if record.village_id else 'Unknown'
                            filename = f'Section11_{project_name}_{village_name}_{record.name or record.id}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating PDF for Section 11 record {record.id}: {str(e)}", exc_info=True)
                    continue
            
            # Generate Section 19 PDFs
            for record in records['section19']:
                try:
                    report_action = self.env.ref('bhuarjan.action_report_section19_notification')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name,
                        [record.id],
                        data={}
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (record.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if record.project_id else 'Unknown'
                            village_name = (record.village_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if record.village_id else 'Unknown'
                            filename = f'Section19_{project_name}_{village_name}_{record.name or record.id}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating PDF for Section 19 record {record.id}: {str(e)}", exc_info=True)
                    continue
            
            # Generate Section 21 PDFs - One PDF per village (contains public notice + all personal notices)
            # Group by (project, village) to ensure only one PDF per village per project
            # Note: Section 21 has unique constraint on (project_id, village_id), so there should be max one per combination
            section21_by_key = {}
            for record in records.get('section21', []):
                if record.village_id and record.project_id:
                    # Create unique key from project and village
                    key = (record.project_id.id, record.village_id.id)
                    # Only keep the first record per (project, village) combination
                    if key not in section21_by_key:
                        section21_by_key[key] = record
            
            # Generate one PDF per village (each PDF contains public notice + all personal notices)
            for key, record in section21_by_key.items():
                try:
                    report_action = self.env.ref('bhuarjan.action_report_section21_notification')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name,
                        [record.id],
                        data={}
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (record.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if record.project_id else 'Unknown'
                            village_name = (record.village_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if record.village_id else 'Unknown'
                            # One PDF per village - filename includes village name only
                            filename = f'Section21_{project_name}_{village_name}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating PDF for Section 21 record {record.id}: {str(e)}", exc_info=True)
                    continue
            
            # Generate SIA Proposal PDFs (project level)
            for sia_team in records.get('sia_teams', []):
                try:
                    # Generate SIA Proposal (Collector's Order template)
                    report_action = self.env.ref('bhuarjan.action_report_sia_proposal')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name,
                        [sia_team.id],
                        data={}
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (sia_team.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if sia_team.project_id else 'Unknown'
                            filename = f'SIA_Proposal_{project_name}_{sia_team.name or sia_team.id}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating SIA Proposal PDF for SIA team {sia_team.id}: {str(e)}", exc_info=True)
                    continue
            
            # Generate SIA Order PDFs (project level)
            for sia_team in records.get('sia_teams', []):
                try:
                    # Generate SIA Order (SDM's Proposal template)
                    report_action = self.env.ref('bhuarjan.action_report_sia_order')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name,
                        [sia_team.id],
                        data={}
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (sia_team.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if sia_team.project_id else 'Unknown'
                            filename = f'SIA_Order_{project_name}_{sia_team.name or sia_team.id}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating SIA Order PDF for SIA team {sia_team.id}: {str(e)}", exc_info=True)
                    continue
            
            # Generate Expert Committee Proposal PDFs (project level)
            for expert_committee in records.get('expert_committees', []):
                try:
                    report_action = self.env.ref('bhuarjan.action_report_expert_committee_proposal')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name,
                        [expert_committee.id],
                        data={}
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (expert_committee.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if expert_committee.project_id else 'Unknown'
                            filename = f'Expert_Committee_Proposal_{project_name}_{expert_committee.name or expert_committee.id}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating Expert Committee Proposal PDF for record {expert_committee.id}: {str(e)}", exc_info=True)
                    continue
            
            # Generate Expert Committee Order PDFs (project level)
            for expert_committee in records.get('expert_committees', []):
                try:
                    report_action = self.env.ref('bhuarjan.action_report_expert_committee_order')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name,
                        [expert_committee.id],
                        data={}
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (expert_committee.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if expert_committee.project_id else 'Unknown'
                            filename = f'Expert_Committee_Order_{project_name}_{expert_committee.name or expert_committee.id}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating Expert Committee Order PDF for record {expert_committee.id}: {str(e)}", exc_info=True)
                    continue
            
            # Generate Form 10 PDFs (grouped by village)
            for village_id in records.get('form10', []):
                try:
                    village = self.env['bhu.village'].browse(village_id)
                    if not village:
                        continue
                    
                    # Get surveys for this village
                    survey_domain = [('village_id', '=', village_id)]
                    if self.project_id:
                        survey_domain.append(('project_id', '=', self.project_id.id))
                    elif self.department_id:
                        # Get all projects in department
                        project_ids = self.env['bhu.project'].search([
                            ('department_id', '=', self.department_id.id)
                        ]).ids
                        if project_ids:
                            survey_domain.append(('project_id', 'in', project_ids))
                    
                    surveys = self.env['bhu.survey'].search(survey_domain)
                    if not surveys:
                        continue
                    
                    # Get first survey for project context
                    first_survey = surveys[0]
                    
                    # Generate Form 10 PDF - pass all survey IDs so the report includes all surveys
                    report_action = self.env.ref('bhuarjan.action_report_form10_bulk_table')
                    pdf_result = report_action.sudo()._render_qweb_pdf(
                        report_action.report_name,
                        surveys.ids,  # Pass all survey IDs for the village
                        data={
                            'village_id': village_id,
                            'project_id': first_survey.project_id.id if first_survey.project_id else False,
                        }
                    )
                    
                    if pdf_result:
                        pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
                        if isinstance(pdf_data, bytes):
                            project_name = (first_survey.project_id.name or 'Unknown').replace('/', '_').replace('\\', '_') if first_survey.project_id else 'Unknown'
                            village_name = (village.name or 'Unknown').replace('/', '_').replace('\\', '_')
                            filename = f'Form10_{project_name}_{village_name}.pdf'
                            zip_file.writestr(filename, pdf_data)
                            pdf_count += 1
                except Exception as e:
                    _logger.error(f"Error generating Form 10 PDF for village {village_id}: {str(e)}", exc_info=True)
                    continue
            
            zip_file.close()
            
            if pdf_count == 0:
                raise ValidationError(_('No PDF reports found for the selected filters.'))
            
            # Create attachment
            zip_buffer.seek(0)
            zip_data = base64.b64encode(zip_buffer.read())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = (self.project_id.name or 'All').replace('/', '_').replace('\\', '_') if self.project_id else 'All'
            filename = f'PDF_Reports_{project_name}_{timestamp}.zip'
            
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': zip_data,
                'mimetype': 'application/zip',
                'res_model': 'bhu.process.report.wizard',
                'res_id': self.id,
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
            
        except Exception as e:
            zip_file.close()
            _logger.error(f"Error creating PDF zip file: {str(e)}", exc_info=True)
            raise ValidationError(_('Error generating PDF zip file: %s') % str(e))

