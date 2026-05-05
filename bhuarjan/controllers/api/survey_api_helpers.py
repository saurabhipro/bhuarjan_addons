# -*- coding: utf-8 -*-
"""Shared helpers for survey/mobile REST API controllers."""


class SurveyAPIHelperMixin:
    """Mixin with shared helper methods for REST controllers."""
    def _get_selection_label(self, record, field_name, value):
        """Get the label for a selection field value"""
        if not value:
            return ''
        try:
            field = record._fields.get(field_name)
            if not field:
                return ''
            selection = field.selection
            # Handle callable selection (dynamic selection)
            if callable(selection):
                selection = selection(record)
            # Convert to dict and get label
            selection_dict = dict(selection) if selection else {}
            return selection_dict.get(value, '')
        except Exception:
            return ''
