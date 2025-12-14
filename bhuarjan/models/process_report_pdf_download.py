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
                        'q1_brief_description': record.q1_brief_description,
                        'q2_directly_affected': record.q2_directly_affected,
                        'q3_indirectly_affected': record.q3_indirectly_affected,
                        'q4_private_assets': record.q4_private_assets,
                        'q5_government_assets': record.q5_government_assets,
                        'q6_minimal_acquisition': record.q6_minimal_acquisition,
                        'q7_alternatives_considered': record.q7_alternatives_considered,
                        'q8_total_cost': record.q8_total_cost,
                        'q9_project_benefits': record.q9_project_benefits,
                        'q10_compensation_measures': record.q10_compensation_measures,
                        'q11_other_components': record.q11_other_components,
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

