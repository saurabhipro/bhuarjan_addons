surveys = env['bhu.survey'].search([])
print("Surveys count:", len(surveys))
for s in surveys[:5]:
    print(f"Survey {s.id}: Khasra={s.khasra_number}, Village={s.village_id.name}")

sims = env['bhu.award.simulator'].search([], order="id desc", limit=1)
if sims:
    s = sims[0]
    print("Simulator ID:", s.id, "Village:", s.village_id.name)
    try:
        land = s.get_land_compensation_data()
        print("Land data len:", len(land))
        if len(land) == 0:
            surveys_for_village = env['bhu.survey'].search([('village_id', '=', s.village_id.id), ('khasra_number', '!=', False)])
            print("Why zero? Surveys for this village with Khasra:")
            for sv in surveys_for_village:
                print(f"  - ID: {sv.id}, State: {sv.state}, Khasra: {sv.khasra_number}")
    except Exception as e:
        print("Error getting land data:", e)
