import re

with open('blueprints/control.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove all occurrences of the block
block_regex = re.compile(r'# ==========================================\s*# CREW SEARCH API \(FOR CNL TOP SEARCH BAR\)\s*# ==========================================.*?return jsonify\(\{\s*"lobbies": sorted_lobbies,\s*"designations": sorted\(list\(designations_set\)\)\s*\}\)\s*', re.DOTALL)

clean_text = block_regex.sub('', text)

search_api_block = '''

# ==========================================
# CREW SEARCH API (FOR CNL TOP SEARCH BAR)
# ==========================================
@control_bp.route('/api/search')
@control_bp.route('/tools/api/search')
def api_search_crew():
    q = request.args.get("q", "").strip()
    lobby = request.args.get("lobby", "").strip()
    desig = request.args.get("desig", "").strip()

    if not q and not lobby and not desig:
        return jsonify([])

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        conditions = []
        params = []

        if q:
            mobile_q = q.replace(" ", "").replace("-", "").replace("+", "")
            if mobile_q.isdigit():
                if mobile_q.startswith('91') and len(mobile_q) >= 11:
                    mobile_q = mobile_q[2:]
                elif mobile_q.startswith('0') and len(mobile_q) >= 11:
                    mobile_q = mobile_q[1:]

            search_term = f"%{q}%"
            mobile_search_term = f"%{mobile_q}%"

            conditions.append("(crew_name LIKE %s OR crew_id LIKE %s OR mobile LIKE %s OR cli_name LIKE %s)")
            params.extend([search_term, search_term, mobile_search_term, search_term])

        if lobby:
            conditions.append("(UPPER(TRIM(crew_hq)) = %s OR crew_id LIKE %s)")
            params.extend([lobby.upper(), f"{lobby.upper()}%"])

        if desig:
            conditions.append("designation = %s")
            params.append(desig)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT id, crew_id, crew_name, designation, crew_hq, mobile, cli_name
            FROM crew_master
            WHERE {where_clause}
            LIMIT 30
        """

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            crew_id_val = str(r.get('crew_id') or '').strip()
            crew_name_val = str(r.get('crew_name') or '').strip()
            hq_val = str(r.get('crew_hq') or '').strip()
            if not hq_val:
                hq_val = ''.join([c for c in crew_id_val if c.isalpha()]).upper()

            formatted_name = f"{crew_name_val}/{hq_val}" if (crew_name_val and hq_val) else crew_name_val

            mob_val = str(r.get('mobile') or '').strip()
            if mob_val.startswith('91') and len(mob_val) > 10:
                mob_val = mob_val[2:]
            elif mob_val.startswith('+91') and len(mob_val) > 11:
                mob_val = mob_val[3:]
            elif mob_val.startswith('0') and len(mob_val) > 10:
                mob_val = mob_val[1:]

            cli_val = str(r.get('cli_name') or '').strip()
            if cli_val in ('-', 'NA', 'N/A', 'NONE', 'NIL'):
                cli_val = ''

            desig_val = str(r.get('designation') or '').strip()

            results.append({
                "crew_id": crew_id_val,
                "crew_name": crew_name_val,
                "formatted_name": formatted_name,
                "mobile_no": mob_val or "-",
                "cli_name": cli_val or "N/A",
                "crew_type": desig_val,
                "designation": desig_val,
                "lobby": hq_val
            })

        return jsonify(results)
    except Exception as e:
        logger.error(f"Error querying crew search: {e}")
        return jsonify([])


@control_bp.route('/api/crew/filters')
@control_bp.route('/tools/api/crew/filters')
def api_crew_search_filters():
    lobbies_set = {"RPH", "BWN", "HWH", "PKR", "DKAE", "AZ", "BDC", "BGP", "DUMK", "SDAH", "MLDT"}
    designations_set = {"ALP", "LPG", "LPM", "LPP", "LPS", "SALP", "SR.LP"}

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT DISTINCT UPPER(TRIM(crew_hq)) as hq FROM crew_master WHERE crew_hq IS NOT NULL AND crew_hq != ''")
        for r in cur.fetchall():
            hq = r.get('hq') if isinstance(r, dict) else r[0]
            if hq:
                lobbies_set.add(hq)

        cur.execute("SELECT DISTINCT designation FROM crew_master WHERE designation IS NOT NULL AND designation != ''")
        for r in cur.fetchall():
            desig = r.get('designation') if isinstance(r, dict) else r[0]
            if desig:
                designations_set.add(desig)

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error querying filters: {e}")

    primary_lobbies = ["RPH", "BWN", "HWH", "PKR", "DKAE"]
    other_lobbies = sorted([l for l in lobbies_set if l not in primary_lobbies])
    sorted_lobbies = primary_lobbies + other_lobbies

    return jsonify({
        "lobbies": sorted_lobbies,
        "designations": sorted(list(designations_set))
    })
'''

clean_text += search_api_block

with open('blueprints/control.py', 'w', encoding='utf-8') as f:
    f.write(clean_text)

print('Cleaned and added single search API block!')
