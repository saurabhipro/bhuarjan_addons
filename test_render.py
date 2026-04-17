import logging
import sys

# Get Odoo environment natively
# Env is already in globals

sims = env['bhu.award.simulator'].search([], order="id desc", limit=1)
if not sims:
    print("No simulator found!")
else:
    s = sims[0]
    print(f"Simulator ID: {s.id}, Village: {s.village_id.name}")

    all_villages = env['bhu.village'].search([])
    for v in all_villages:
        if 'Jurda' in v.name or 'जु' in v.name:
            cnt = env['bhu.survey'].search_count([('village_id', '=', v.id)])
            print(f"Village {v.id} (xml_id: {v.get_metadata()[0].get('xmlid')}): {v.name} -> {cnt} surveys")
        
    try:
        land_data = s.get_land_compensation_data()
        print(f"Land Data len={len(land_data)}")
        if len(land_data) > 0:
            print("Row 0:", land_data[0])
    except Exception as e:
        print("EXCEPTION IN get_land_compensation_data:", e)

    print("Attempting to render award_simulator_report template...")
    try:
        # Directly render the qweb template given the context
        html = env['ir.qweb']._render('bhuarjan.award_simulator_report', {'docs': sims})
        print(f"RENDER OK! Length of HTML: {len(html)} bytes")
        with open('output_test.html', 'wb') as f:
            f.write(html.encode('utf8')) if isinstance(html, str) else f.write(html)
        print("Written to output_test.html")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("EXCEPTION IN RENDER:", e)
