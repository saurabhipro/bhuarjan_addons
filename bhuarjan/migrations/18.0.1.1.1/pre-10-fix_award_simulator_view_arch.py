# -*- coding: utf-8 -*-
# Pre-phase runs before the module (and its XML) is loaded. Fix stored arch
# that had ``<=`` in help/tooltip text: Odoo's translation layer parses
# translatable terms as XML, and a literal ``<=`` breaks lxml (column ~18).
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT v.id, v.arch_db
        FROM ir_ui_view v
        JOIN ir_model_data d ON d.res_id = v.id AND d.model = 'ir.ui.view'
        WHERE d.module = %s AND d.name = %s
        """,
        ("bhuarjan", "view_bhu_award_simulator_form"),
    )
    row = cr.fetchone()
    if not row or not row[1]:
        return
    view_id, arch = row[0], row[1]
    if "&lt;=" not in arch and "<=" not in arch:
        return
    new_arch = arch
    new_arch = new_arch.replace("Rural uses &lt;= 50m", "Rural: 50m")
    new_arch = new_arch.replace("Urban uses &lt;= 20m", "Urban: 20m")
    new_arch = new_arch.replace("distance &lt;= 50 m", "within 50 m")
    new_arch = new_arch.replace("distance &lt;= 20 m", "within 20 m")
    # Broken or hand-edited XML (invalid but sometimes present in DB exports)
    new_arch = new_arch.replace("Rural uses <= 50m", "Rural: 50m")
    new_arch = new_arch.replace("Urban uses <= 20m", "Urban: 20m")
    if new_arch == arch:
        return
    cr.execute("UPDATE ir_ui_view SET arch_db = %s WHERE id = %s", (new_arch, view_id))
    _logger.info(
        "bhuarjan: pre-migration repaired arch_db for view_bhu_award_simulator_form (id=%s)",
        view_id,
    )
