# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64


class SIADownloadWizard(models.TransientModel):
    _name = 'sia.download.wizard'
    _description = 'SIA Download Format Wizard'

    sia_team_id = fields.Many2one('bhu.sia.team', string='SIA Team', required=True)
    format = fields.Selection([
        ('pdf', 'PDF Format'),
        ('word', 'Word Format (.doc)')
    ], string='Download Format', default='pdf', required=True)

    def action_download(self):
        """Download the SIA Proposal in selected format"""
        self.ensure_one()
        
        if self.format == 'pdf':
            # Download as PDF using standard report
            return self.env.ref('bhuarjan.action_report_sia_proposal').report_action(self.sia_team_id)
        else:
            # Download as Word (.doc) - HTML format that Word can open
            return self._generate_word_doc()
    
    def _generate_word_doc(self):
        """Generate Word document from report HTML with embedded images and inline styles"""
        self.ensure_one()
        
        # Get the HTML content from the report
        report = self.env.ref('bhuarjan.action_report_sia_proposal')
        html_content, report_format = report._render_qweb_html(report.report_name, [self.sia_team_id.id])
        
        # Convert bytes to string if needed
        html_str = html_content.decode('utf-8') if isinstance(html_content, bytes) else html_content
        
        import re
        import base64
        import requests
        
        # Remove all <link> and <script> tags that reference external files
        html_str = re.sub(r'<link[^>]*>', '', html_str)
        html_str = re.sub(r'<script[^>]*>.*?</script>', '', html_str, flags=re.DOTALL)
        
        # Extract inline styles
        style_pattern = r'<style[^>]*>(.*?)</style>'
        styles = re.findall(style_pattern, html_str, re.DOTALL)
        combined_styles = '\n'.join(styles)
        
        # Convert images to base64 data URIs
        def convert_image_to_base64(match):
            img_tag = match.group(0)
            src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
            if not src_match:
                return img_tag
            
            img_url = src_match.group(1)
            
            try:
                # Handle relative URLs
                if img_url.startswith('/'):
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
                    img_url = base_url + img_url
                
                # Fetch the image
                response = requests.get(img_url, timeout=5)
                if response.status_code == 200:
                    img_base64 = base64.b64encode(response.content).decode('utf-8')
                    # Determine mime type from response headers or URL
                    content_type = response.headers.get('content-type', 'image/png')
                    data_uri = f'data:{content_type};base64,{img_base64}'
                    return img_tag.replace(src_match.group(1), data_uri)
            except:
                pass
            
            return img_tag
        
        # For Word format, remove ALL images (QR codes and logos) to save space
        html_str = re.sub(r'<img[^>]*>', '', html_str)
        
        # Also remove image containers that might leave empty space
        html_str = re.sub(r'<div[^>]*class="[^"]*qr[^"]*"[^>]*>.*?</div>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
        html_str = re.sub(r'<div[^>]*class="[^"]*logo[^"]*"[^>]*>.*?</div>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove inline styles that add spacing - but keep table structure
        # Don't remove border/padding from td/th elements
        html_str = re.sub(r'<(?!td|th|table)([^>]+)style="[^"]*border[^"]*"', r'<\1style=""', html_str, flags=re.IGNORECASE)
        html_str = re.sub(r'<(?!td|th|table)([^>]+)style="[^"]*padding[^"]*"', r'<\1style=""', html_str, flags=re.IGNORECASE)
        html_str = re.sub(r'<(?!td|th|table)([^>]+)style="[^"]*margin[^"]*"', r'<\1style=""', html_str, flags=re.IGNORECASE)
        
        # Remove empty style attributes
        html_str = re.sub(r'\s*style=""\s*', ' ', html_str)
        
        # Clean up styles - remove @page rules that cause issues
        combined_styles = re.sub(r'@page[^{]*\{[^}]*\}', '', combined_styles)
        
        # Word-compatible HTML wrapper - NO XML declaration, pure HTML
        word_html = f"""<html xmlns:o='urn:schemas-microsoft-com:office:office' 
      xmlns:w='urn:schemas-microsoft-com:office:word'
      xmlns='http://www.w3.org/TR/REC-html40'>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <meta name="ProgId" content="Word.Document"/>
    <meta name="Generator" content="Microsoft Word 15"/>
    <meta name="Originator" content="Microsoft Word 15"/>
    <!--[if gte mso 9]>
    <xml>
        <w:WordDocument>
            <w:View>Print</w:View>
            <w:Zoom>100</w:Zoom>
            <w:DoNotOptimizeForBrowser/>
        </w:WordDocument>
    </xml>
    <![endif]-->
    <style type="text/css">
        /* Original report styles - inline and self-contained */
        {combined_styles}
        
        /* Word compatibility styles - MINIMAL margins for maximum space */
        body {{
            font-family: 'Noto Sans Devanagari', 'Mangal', 'Arial Unicode MS', Arial, sans-serif !important;
            font-size: 11pt;
            line-height: 1.2;
            margin-top: 0.1in !important;
            margin-bottom: 0.1in !important;
            margin-left: 0.15in !important;
            margin-right: 0.15in !important;
            padding: 0 !important;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0 !important;
            padding: 0 !important;
        }}
        
        /* Hide all images (QR codes and logos removed for Word format) */
        img {{
            display: none !important;
        }}
        
        /* Hide empty image containers */
        .qr_code, .o_company_logo, [class*="logo"], [class*="qr"] {{
            display: none !important;
        }}
        
        /* Remove decorative borders and boxes to save space */
        div[style*="border"], .o_border, [class*="border"], div[style*="box"] {{
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        
        /* Remove dotted/dashed borders */
        * {{
            border-style: none !important;
            outline: none !important;
        }}
        
        table {{
            border-collapse: collapse !important;
            width: 100% !important;
            mso-table-lspace: 0pt !important;
            mso-table-rspace: 0pt !important;
            margin: 2px 0 !important;
            padding: 0 !important;
            border: 1px solid #000 !important;
        }}
        
        /* All tables should have borders */
        td, th {{
            border: 1px solid #000 !important;
            padding: 3px 5px !important;
            margin: 0 !important;
            mso-line-height-rule: exactly;
            vertical-align: top;
            text-align: left;
        }}
        
        /* Table headers */
        th {{
            font-weight: bold !important;
            background-color: #f0f0f0 !important;
        }}
        
        /* Ensure proper table structure */
        tbody, thead, tfoot {{
            border: 1px solid #000 !important;
        }}
        
        tr {{
            border: 1px solid #000 !important;
        }}
        
        p {{
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.1 !important;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            margin: 1px 0 !important;
            padding: 0 !important;
            line-height: 1.1 !important;
        }}
        
        /* ULTRA Compact layout - minimal spacing */
        div, section, article, span {{
            padding: 0 !important;
            margin: 0 !important;
        }}
        
        /* Data tables should have visible borders */
        .o_main_table, .o_data_table, table[border] {{
            border: 1px solid #000 !important;
        }}
        
        .o_main_table td, .o_data_table td, table[border] td {{
            border: 1px solid #000 !important;
            padding: 3px 5px !important;
        }}
        
        /* Clean tables without data keep minimal styling */
        .o_clean_table {{
            border: none !important;
        }}
        
        .o_clean_table td {{
            border: none !important;
            padding: 1px !important;
            margin: 0 !important;
        }}
        
        /* Remove page containers and decorative elements */
        .page, .o_page, [class*="container"] {{
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
        }}
        
        /* Compact text blocks */
        .o_text_block, .text-block {{
            margin: 0 !important;
            padding: 0 !important;
        }}
    </style>
</head>
<body lang="EN-IN">
    {html_str}
</body>
</html>"""
        
        # Generate filename
        project_name = self.sia_team_id.project_id.name or 'Project'
        project_name = project_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
        date_str = self.sia_team_id.create_date.strftime('%Y%m%d') if self.sia_team_id.create_date else 'Date'
        filename = f'SIA_Proposal_{project_name}_{date_str}.doc'
        
        # Encode to base64
        word_data = base64.b64encode(word_html.encode('utf-8'))
        
        # Create attachment and download
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': word_data,
            'res_model': 'bhu.sia.team',
            'res_id': self.sia_team_id.id,
            'mimetype': 'application/msword'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
