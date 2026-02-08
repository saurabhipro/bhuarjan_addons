# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class BhuarjanWebsite(http.Controller):

    @http.route(['/'], type='http', auth="public", website=True)
    def index(self, **post):
        """
        Custom homepage for BHUARJAN.
        Fetches dynamic stats for the 'Real Time Insights' section.
        """
        # Fetch stats from bhuarjan models
        # Note: In a real scenario, we might want to cache these or use a specific model for public stats
        Project = request.env['bhu.project'].sudo()
        Survey = request.env['bhu.survey'].sudo()
        
        stats = {
            'total_projects': Project.search_count([]),
            'ongoing_projects': Project.search_count([('state', 'not in', ['approved', 'rejected'])]),
            'total_surveys': Survey.search_count([]),
            'approved_surveys': Survey.search_count([('state', '=', 'approved')]),
        }
        
        return request.render('bhuarjan_website.homepage', {
            'stats': stats,
        })
