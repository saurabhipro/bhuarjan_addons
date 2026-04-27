# -*- coding: utf-8 -*-

from odoo import models


class Section23AwardData(models.Model):
    _inherit = 'bhu.section23.award'

    def get_land_compensation_data(self):
        """Get land compensation data grouped by landowner and khasra"""
        self.ensure_one()
        acre_per_hectare = 2.471

        # Get approved surveys for this village and project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['draft', 'submitted', 'approved', 'locked']),
            ('khasra_number', '!=', False),
        ])

        if not surveys:
            return []

        # Group by landowner and khasra
        compensation_data = {}

        for survey in surveys:
            khasra = survey.khasra_number or ''
            acquired_area = survey.acquired_area or 0.0
            total_area = survey.total_area or acquired_area or 0.0

            # Get land type from survey
            irrigation_type = survey.irrigation_type or 'unirrigated'
            is_irrigated = irrigation_type == 'irrigated'
            is_unirrigated = irrigation_type == 'unirrigated'
            is_fallow = self._is_fallow_survey(survey)
            is_diverted = survey.has_traded_land == 'yes'

            # Get landowners for this survey
            landowners = survey.landowner_ids if survey.landowner_ids else []

            if not landowners:
                # If no landowners, create entry with empty landowner
                key = (False, khasra)
                if key not in compensation_data:
                    compensation_data[key] = {
                        'landowner': None,
                        'landowner_name': '',
                        'father_name': '',
                        'address': '',
                        'khasra': khasra,
                        'original_area': 0.0,
                        'acquired_area': 0.0,
                        'lagan': khasra,  # Using khasra as lagan
                        'fallow': is_fallow,
                        'unirrigated': False,
                        'irrigated': False,
                        'is_diverted': is_diverted,
                        'guide_line_rate': 0.0,
                        'market_value': 0.0,
                        'solatium': 0.0,
                        'interest': 0.0,
                        'total_compensation': 0.0,
                        'rehab_policy_per_acre_1': 0.0,
                        'rehab_policy_per_acre_2': 0.0,
                        'rehab_policy_amount': 0.0,
                        'dev_compensation': 0.0,
                    }
                compensation_data[key]['original_area'] += total_area
                compensation_data[key]['acquired_area'] += acquired_area
            else:
                # Process each landowner
                for landowner in landowners:
                    key = (landowner.id, khasra)
                    if key not in compensation_data:
                        compensation_data[key] = {
                            'landowner': landowner,
                            'landowner_name': landowner.name or '',
                            'father_name': landowner.father_name or '',
                            'spouse_name': landowner.spouse_name or '',
                            'address': landowner.owner_address or '',
                            'khasra': khasra,
                            'original_area': 0.0,
                            'acquired_area': 0.0,
                            'lagan': khasra,
                            'fallow': is_fallow,
                            'unirrigated': is_unirrigated,
                            'irrigated': is_irrigated,
                            'is_diverted': is_diverted,
                            'guide_line_rate': 0.0,  # Will be calculated
                            'market_value': 0.0,
                            'solatium': 0.0,
                            'interest': 0.0,
                            'total_compensation': 0.0,
                            'rehab_policy_per_acre_1': 0.0,
                            'rehab_policy_per_acre_2': 0.0,
                            'rehab_policy_amount': 0.0,
                            'dev_compensation': 0.0,
                        }
                    compensation_data[key]['original_area'] += total_area
                    compensation_data[key]['acquired_area'] += acquired_area

        # Convert to list and calculate totals
        result = []
        # Convert to list and calculate totals matching the 19 columns
        result = []
        for _key, data in compensation_data.items():
            # Get survey to access proper rates if possible
            survey = self.env['bhu.survey'].search([
                ('project_id', '=', self.project_id.id),
                ('village_id', '=', self.village_id.id),
                ('khasra_number', '=', data['khasra'])
            ], limit=1)

            # Derive main-road status from measured distance.
            # Rule: rural <= 50m is MR, urban <= 30m is MR; 0/blank counts as MR.
            distance_from_main_road = (survey.distance_from_main_road or 0.0) if survey else 0.0
            if survey:
                threshold = 50.0 if survey.survey_type == 'rural' else 30.0
                derived_is_within_distance = distance_from_main_road <= threshold
            else:
                derived_is_within_distance = False

            # Guide column = rate master only (village + main road vs other road).
            # Basic value uses effective rate (master × irrigation × diverted) from survey line compute.
            award_line = self.award_survey_line_ids.filtered(lambda l: l.survey_id.id == survey.id)
            has_award_line = bool(award_line)
            is_within_distance = derived_is_within_distance
            is_diverted = survey.has_traded_land == 'yes' if survey else False

            al_rec = award_line[:1] if has_award_line else self.env['bhu.section23.award.survey.line']
            base_rate_ha = self._s23_land_base_rate_per_hectare(survey, al_rec, derived_is_within_distance)

            if has_award_line:
                guide_line_rate = award_line[0].guide_line_master_rate or base_rate_ha
                effective_rate = award_line[0].rate_per_hectare or base_rate_ha
            else:
                guide_line_rate = base_rate_ha if base_rate_ha else 2112000.0
                effective_rate = guide_line_rate
                if survey:
                    itype = survey.irrigation_type or False
                    if itype == 'irrigated':
                        effective_rate *= 1.2
                    elif itype in ('non_irrigated', 'unirrigated'):
                        effective_rate *= 0.8
                if is_diverted and derived_is_within_distance:
                    effective_rate *= 1.25

            # Logic matching 19-column image:
            # 13: basic_value = effective rate * area (irrigation/diverted on top of master)
            # 14: market_value = basic_value * factor (2)
            # 15: solatium = market_value * 1.0
            # 16: interest = 1% per month on basic value from section 4 hearing to award date

            market_value_basic = data['acquired_area'] * effective_rate
            market_value_factored = market_value_basic * 2.0
            solatium = market_value_factored * 1.0  # 100%

            interest, _days = self._calculate_interest_on_basic(market_value_basic)

            total_compensation = market_value_factored + solatium + interest
            acquired_area_acre = data['acquired_area'] * acre_per_hectare
            rehab_rate_per_acre = self._get_min_rehab_rate_per_acre(
                data.get('fallow'),
                data.get('irrigated'),
                data.get('unirrigated'),
            )
            rehab_policy_amount = acquired_area_acre * rehab_rate_per_acre
            payable_compensation = max(total_compensation, rehab_policy_amount)

            if survey and self._is_fallow_survey(survey):
                irrigation_label = 'Fallow / पड़ती'
            elif survey and survey.irrigation_type == 'irrigated':
                irrigation_label = 'Irrigated / सिंचित'
            else:
                irrigation_label = 'Unirrigated / असिंचित'
            village_name = (self.village_id.name or '') if self.village_id else ''
            road_lbl = 'MR' if is_within_distance else 'BMR'
            diverted_lbl = 'Yes' if is_diverted else 'No'

            data.update({
                'guide_line_rate': guide_line_rate,
                'basic_value': market_value_basic,
                'market_value': market_value_factored,
                'solatium': solatium,
                'interest': interest,
                'total_compensation': total_compensation,
                'rehab_policy_rate_per_acre': rehab_rate_per_acre,
                'rehab_policy_amount': rehab_policy_amount,
                'paid_compensation': payable_compensation,
                'remark': '',
                'original_area': survey.total_area if survey else 0.0,
                'lagan': survey.lagan if (survey and hasattr(survey, 'lagan')) else data['khasra'],
                'is_within_distance': is_within_distance,
                'distance_from_main_road': distance_from_main_road,
                'is_diverted': is_diverted,
                'village_name': village_name,
                'base_rate_hectare': base_rate_ha,
                'effective_rate_hectare': effective_rate,
                'road_type_label': road_lbl,
                'irrigation_label': irrigation_label,
                'diverted_label': diverted_lbl,
                'survey_id': survey.id if survey else False,
            })

            result.append(data)

        # Sort by landowner name, then khasra
        result.sort(key=lambda x: (x['landowner_name'] or '', x['khasra'] or ''))

        return result

    def get_land_compensation_grouped_data(self):
        """Group land rows by owner so multiple khasras appear together."""
        self.ensure_one()
        land_data = self.get_land_compensation_data()
        grouped = {}
        ordered_keys = []

        def _khasra_sort_key(line):
            khasra = (line.get('khasra') or '').strip()
            if not khasra:
                return (1, 10**12, 10**12, '')
            parts = khasra.split('/', 1)
            main = int(parts[0]) if parts[0].isdigit() else 10**12
            sub = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10**12
            return (0, main, sub, khasra)

        numeric_totals = (
            'original_area', 'acquired_area', 'basic_value', 'market_value',
            'solatium', 'interest', 'total_compensation', 'rehab_policy_amount', 'paid_compensation',
        )
        for row in land_data:
            if row.get('landowner_name'):
                # Group by beneficiary identity (name + father/spouse) so duplicate
                # landowner master IDs with same beneficiary still merge in one block.
                beneficiary_name = (row.get('landowner_name') or '').strip().lower()
                father_name = (row.get('father_name') or '').strip().lower()
                key = ('beneficiary', beneficiary_name, father_name)
            else:
                key = ('khasra', row.get('khasra') or '')
            if key not in grouped:
                grouped[key] = {
                    'landowner_name': row.get('landowner_name', ''),
                    'father_name': row.get('father_name', ''),
                    'spouse_name': row.get('spouse_name', ''),
                    'address': row.get('address', ''),
                    'lines': [],
                    'khasra_count': 0,
                    'khasra_seen': set(),
                }
                for field_name in numeric_totals:
                    grouped[key][field_name] = 0.0
                ordered_keys.append(key)
            group = grouped[key]
            group['lines'].append(row)
            khasra = row.get('khasra') or ''
            if khasra and khasra not in group['khasra_seen']:
                group['khasra_seen'].add(khasra)
                group['khasra_count'] += 1
            for field_name in numeric_totals:
                group[field_name] += row.get(field_name, 0.0) or 0.0

        result = []
        for key in ordered_keys:
            group = grouped[key]
            group['lines'] = sorted(group.get('lines', []), key=_khasra_sort_key)
            group.pop('khasra_seen', None)
            result.append(group)
        return result

    def format_indian_number(self, value, decimals=2):
        """Format number with Indian numbering system (commas for thousands)"""
        if value is None:
            value = 0.0

        # Format the number with commas (Indian numbering system)
        if decimals == 2:
            formatted = f"{value:,.2f}"
        elif decimals == 4:
            formatted = f"{value:,.4f}"
        else:
            formatted = f"{value:,.{decimals}f}"

        return formatted

    def get_tree_compensation_data(self):
        """Get tree compensation data grouped by landowner and khasra"""
        self.ensure_one()

        # Get approved surveys with trees for this village and project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['draft', 'submitted', 'approved', 'locked']),
            ('khasra_number', '!=', False),
        ])

        if not surveys:
            return []

        # Get all tree lines from surveys
        tree_data = {}

        for survey in surveys:
            khasra = survey.khasra_number or ''
            landowners = survey.landowner_ids if survey.landowner_ids else []

            # Get tree lines for this survey
            tree_lines = survey.tree_line_ids if hasattr(survey, 'tree_line_ids') else []

            if not tree_lines:
                continue

            if not landowners:
                # If no landowners, create entry with empty landowner
                for tree_line in tree_lines:
                    tree_type_name = tree_line.tree_master_id.name if tree_line.tree_master_id else 'other'
                    key = (False, khasra, tree_type_name)
                    if key not in tree_data:
                        _la = (survey.acquired_area or 0.0) or (survey.total_area or 0.0)
                        tree_data[key] = {
                            'landowner': None,
                            'landowner_name': '',
                            'father_name': '',
                            'khasra': khasra,
                            'total_khasra': '',
                            'total_area': _la,
                            'land_khasra': khasra,
                            'land_area_ha': _la,
                            'tree_khasra': khasra,
                            'mulya': 0.0,
                            'kul_rashi': 0.0,
                            'tree_type': tree_type_name,
                            'tree_type_code': getattr(tree_line, 'tree_type', '') or 'other',
                            'tree_count': 0,
                            'girth_cm': 0.0,
                            'unit_rate': 0.0,
                            'rate': 0.0,
                            'development_stage': getattr(tree_line, 'development_stage', '') or '',
                            'condition': getattr(tree_line, 'condition', '') or '',
                            'value': 0.0,
                            'determined_value': 0.0,
                            'solatium': 0.0,
                            'interest': 0.0,
                            'total': 0.0,
                            'remark': '',
                        }
                    rate_per_tree = tree_line.get_applicable_rate() if hasattr(tree_line, 'get_applicable_rate') else 0.0
                    tree_data[key]['tree_count'] += tree_line.quantity or 0
                    tree_data[key]['girth_cm'] = getattr(tree_line, 'girth_cm', 0.0) or 0.0
                    tree_data[key]['rate'] = rate_per_tree
                    tree_data[key]['unit_rate'] = rate_per_tree
                    tree_data[key]['development_stage'] = getattr(tree_line, 'development_stage', '') or ''
                    tree_data[key]['condition'] = getattr(tree_line, 'condition', '') or ''
                    tree_data[key]['value'] += (getattr(tree_line, 'quantity', 0) or 0) * rate_per_tree
            else:
                # Process each landowner
                for landowner in landowners:
                    for tree_line in tree_lines:
                        tree_type_name = tree_line.tree_master_id.name if tree_line.tree_master_id else 'other'
                        key = (landowner.id, khasra, tree_type_name)
                        if key not in tree_data:
                            _la = (survey.acquired_area or 0.0) or (survey.total_area or 0.0)
                            tree_data[key] = {
                                'landowner': landowner,
                                'landowner_name': landowner.name or '',
                                'father_name': landowner.father_name or '',
                                'spouse_name': landowner.spouse_name or '',
                                'khasra': khasra,
                                'total_khasra': khasra,
                                'total_area': _la,
                                'land_khasra': khasra,
                                'land_area_ha': _la,
                                'tree_khasra': khasra,
                                'mulya': 0.0,
                                'kul_rashi': 0.0,
                                'tree_type': tree_line.tree_master_id.name if tree_line.tree_master_id else 'other',
                                'tree_type_code': getattr(tree_line, 'tree_type', '') or 'other',
                                'tree_count': 0,
                                'girth_cm': 0.0,
                                'unit_rate': 0.0,
                                'rate': 0.0,
                                'development_stage': getattr(tree_line, 'development_stage', '') or '',
                                'condition': getattr(tree_line, 'condition', '') or '',
                                'value': 0.0,
                                'determined_value': 0.0,
                                'solatium': 0.0,
                                'interest': 0.0,
                                'total': 0.0,
                                'remark': '',
                            }
                        rate_per_tree = tree_line.get_applicable_rate() if hasattr(tree_line, 'get_applicable_rate') else 0.0
                        tree_data[key]['tree_count'] += getattr(tree_line, 'quantity', 0) or 0
                        tree_data[key]['girth_cm'] = getattr(tree_line, 'girth_cm', 0.0) or 0.0
                        tree_data[key]['unit_rate'] = rate_per_tree
                        tree_data[key]['rate'] = rate_per_tree
                        tree_data[key]['development_stage'] = getattr(tree_line, 'development_stage', '') or ''
                        tree_data[key]['condition'] = getattr(tree_line, 'condition', '') or ''
                        tree_data[key]['value'] += (getattr(tree_line, 'quantity', 0) or 0) * rate_per_tree

        # Calculate compensation amounts
        result = []
        for _key, data in tree_data.items():
            determined_value = data['value']
            data['mulya'] = determined_value
            data['kul_rashi'] = determined_value
            data['land_khasra'] = data.get('land_khasra') or data.get('khasra') or ''
            data['tree_khasra'] = data.get('tree_khasra') or data.get('khasra') or ''
            data['land_area_ha'] = data.get('land_area_ha', 0.0) or 0.0
            solatium = determined_value * 1.0  # 100% solatium
            interest, _days = self._calculate_interest_on_basic(determined_value)
            total = determined_value + solatium + interest

            data['determined_value'] = determined_value
            data['solatium'] = solatium
            data['interest'] = interest
            data['total'] = total

            result.append(data)

        # Sort by landowner name, then khasra, then tree type
        result.sort(key=lambda x: (x['landowner_name'] or '', x['khasra'] or '', x.get('tree_type', '') or ''))

        return result

    def get_structure_compensation_data(self):
        """Get structure compensation data from shared award structure entries."""
        self.ensure_one()
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['draft', 'submitted', 'approved', 'locked']),
            ('khasra_number', '!=', False),
        ])
        if not surveys:
            return []

        structure_lines = self.env['bhu.award.structure.details'].search([
            ('survey_id', 'in', surveys.ids),
        ])
        if not structure_lines:
            return []

        structure_data = []
        for line in structure_lines:
            survey = line.survey_id
            total_value = line.line_total or 0.0
            base_row = {
                'total_khasra': survey.khasra_number or '',
                'total_area': survey.total_area or 0.0,
                'asset_khasra': survey.khasra_number or '',
                'asset_land_area': survey.acquired_area or 0.0,
                'asset_type': line.get_structure_type_label(),
                'structure_type': line.structure_type or '',
                'construction_type': line.construction_type or '',
                'asset_code': 4,
                'asset_dimension': (
                    (line.asset_count or 0.0)
                    if line.structure_type == 'well'
                    else ((line.area_sqm or 0.0) * (line.asset_count or 0.0))
                ),
                'rate_per_sqm': line.market_rate_per_sqm or 0.0,
                'remark': line.description or '',
            }
            owners = survey.landowner_ids
            # Use first owner for display (consistent with land/tree)
            first_owner = owners[0] if owners else None
            owner_names = ', '.join([o.name for o in owners if o.name]) if owners else ''
            total_interest, _days = self._calculate_interest_on_basic(total_value)
            structure_data.append({
                **base_row,
                'landowner_name': owner_names,
                'father_name': first_owner.father_name if first_owner else '',
                'spouse_name': first_owner.spouse_name if first_owner else '',
                'address': first_owner.owner_address if first_owner else '',
                'market_value': total_value,
                'solatium': total_value,
                'interest': total_interest,
                'total': total_value + total_value + total_interest,
            })
        return structure_data

    def get_tree_compensation_grouped_data(self):
        self.ensure_one()
        tree_data = self.get_tree_compensation_data()
        grouped = {}
        ordered_keys = []
        numeric_totals = (
            'land_area_ha', 'tree_count', 'value', 'mulya', 'kul_rashi',
            'solatium', 'interest', 'total',
        )
        for row in tree_data:
            owner = row.get('landowner')
            khasra = row.get('tree_khasra') or row.get('khasra') or ''
            if owner:
                key = ('owner_khasra', owner.id, khasra)
            elif row.get('landowner_name'):
                key = ('name_khasra', row.get('landowner_name'), row.get('father_name') or '', khasra)
            else:
                key = ('khasra', khasra)
            if key not in grouped:
                grouped[key] = {
                    'landowner_name': row.get('landowner_name', ''),
                    'father_name': row.get('father_name', ''),
                    'spouse_name': row.get('spouse_name', ''),
                    'address': row.get('address', ''),
                    'lines': [],
                    'khasra_count': 0,
                    'khasra_seen': set(),
                }
                for field_name in numeric_totals:
                    grouped[key][field_name] = 0.0
                ordered_keys.append(key)
            group = grouped[key]
            group['lines'].append(row)
            khasra = row.get('tree_khasra') or row.get('khasra') or ''
            if khasra and khasra not in group['khasra_seen']:
                group['khasra_seen'].add(khasra)
                group['khasra_count'] += 1
            for field_name in numeric_totals:
                group[field_name] += row.get(field_name, 0.0) or 0.0

        result = []
        for key in ordered_keys:
            group = grouped[key]
            group.pop('khasra_seen', None)
            result.append(group)
        return result

    def get_structure_compensation_grouped_data(self):
        """Group structure rows by khasra for report rowspans/subtotals."""
        self.ensure_one()
        structure_data = self.get_structure_compensation_data()
        grouped = {}
        ordered_keys = []
        numeric_totals = ('total_area', 'asset_land_area', 'asset_dimension', 'market_value', 'solatium', 'interest', 'total')
        for row in structure_data:
            # Merge all landowners of the same khasra into one group cell.
            key = ('khasra', row.get('asset_khasra') or row.get('total_khasra') or '')
            if key not in grouped:
                grouped[key] = {
                    'landowner_name': '',
                    'father_name': '',
                    'lines': [],
                    'khasra_count': 0,
                    'khasra_seen': set(),
                    'owner_names': [],
                    'owner_seen': set(),
                }
                for field_name in numeric_totals:
                    grouped[key][field_name] = 0.0
                ordered_keys.append(key)
            group = grouped[key]
            owner_name = (row.get('landowner_name') or '').strip()
            if owner_name and owner_name not in group['owner_seen']:
                group['owner_seen'].add(owner_name)
                group['owner_names'].append(owner_name)
            group['lines'].append(row)
            khasra = row.get('asset_khasra') or row.get('total_khasra') or ''
            if khasra and khasra not in group['khasra_seen']:
                group['khasra_seen'].add(khasra)
                group['khasra_count'] += 1
            for field_name in numeric_totals:
                group[field_name] += row.get(field_name, 0.0) or 0.0

        result = []
        for key in ordered_keys:
            group = grouped[key]
            group['landowner_name'] = ', '.join(group['owner_names'])
            group.pop('owner_names', None)
            group.pop('owner_seen', None)
            group.pop('khasra_seen', None)
            result.append(group)
        return result
