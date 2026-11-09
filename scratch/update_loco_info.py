with open(r'templates\public\loco_info.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Header action
hdr_target = """        <div class="mt-2 mt-md-0">
            <span class="badge bg-warning text-dark px-3 py-2 fs-6 shadow-sm">
                <i class="fa-solid fa-bolt me-1"></i> Electric &amp; Diesel Unified Operations
            </span>
        </div>"""

hdr_repl = """        <div class="mt-2 mt-md-0 d-flex gap-2 align-items-center">
            <a href="{{ url_for('public.haulage_capacity') }}" class="btn btn-primary fw-bold shadow-sm">
                <i class="fa-solid fa-gauge-high me-1"></i> Hauling Capacity Calculator (RDSO)
            </a>
            <span class="badge bg-warning text-dark px-3 py-2 fs-6 shadow-sm">
                <i class="fa-solid fa-bolt me-1"></i> Electric &amp; Diesel Unified Operations
            </span>
        </div>"""

assert hdr_target in html, "hdr_target not found"
html = html.replace(hdr_target, hdr_repl, 1)

# 2. Add 4th pill in nav
pill_target = """        <li class="nav-item" role="presentation">
            <button class="nav-link fw-bold" id="guidelines-tab" data-bs-toggle="pill" data-bs-target="#general-guidelines" type="button" role="tab">
                <i class="fa-solid fa-clipboard-check me-1 text-success"></i> Critical Operating Instructions
            </button>
        </li>
    </ul>"""

pill_repl = """        <li class="nav-item" role="presentation">
            <button class="nav-link fw-bold" id="guidelines-tab" data-bs-toggle="pill" data-bs-target="#general-guidelines" type="button" role="tab">
                <i class="fa-solid fa-clipboard-check me-1 text-success"></i> Critical Operating Instructions
            </button>
        </li>
        <li class="nav-item" role="presentation">
            <a class="nav-link fw-bold text-dark bg-warning-subtle border border-warning" href="{{ url_for('public.haulage_capacity') }}">
                <i class="fa-solid fa-calculator me-1 text-danger"></i> ⚡ Hauling Capacity &amp; Load Tables (RDSO &amp; WAG-12B)
            </a>
        </li>
    </ul>"""

assert pill_target in html, "pill_target not found"
html = html.replace(pill_target, pill_repl, 1)

# 3. Add WAG-12B card button
wag12_target = """                                        <tr><th class="bg-light">Weight</th><td>180 tonnes (22.5 tonne axle load, upgradeable to 25t)</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>"""

wag12_repl = """                                        <tr><th class="bg-light">Weight</th><td>180 tonnes (22.5 tonne axle load, upgradeable to 25t)</td></tr>
                                    </tbody>
                                </table>
                            </div>
                            <div class="mt-3">
                                <a href="{{ url_for('public.haulage_capacity') }}#tab-wag12" class="btn btn-warning btn-sm fw-bold w-100">
                                    <i class="fa-solid fa-gauge-high me-1"></i> View WAG-12B Heavy Haul &amp; Momentum Tables
                                </a>
                            </div>
                        </div>"""

assert wag12_target in html, "wag12_target not found"
html = html.replace(wag12_target, wag12_repl, 1)

with open(r'templates\public\loco_info.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("[OK] templates/public/loco_info.html updated successfully!")
