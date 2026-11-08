import os

login_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\templates\auth\login.html"

with open(login_file, 'r', encoding='utf-8') as f:
    html = f.read()

# Update input placeholder and helper text
old_input = '''                        <label for="username" class="form-label fw-bold small text-dark">
                            <i class="fa-solid fa-user me-1 text-primary"></i> Login Identifier (CMS ID / CLI ID / Username / Mobile):
                        </label>
                        <input type="text" class="form-control form-control-lg fs-6" id="username" name="username" placeholder="e.g. admin, Sr. DEE(OP)/HWH, CNL_HWH, CLI_HWH_01, HWH0001, 9876543210" required autofocus>
                        <div class="form-text small">
                            Crew: CMS ID (e.g. HWH0001) or Mobile; CLI: CLI ID or Name; Officer/Admin: Official ID.
                        </div>'''

new_input = '''                        <label for="username" class="form-label fw-bold small text-dark">
                            <i class="fa-solid fa-user me-1 text-primary"></i> Login Identifier (CLI ID / CMS ID / Username / Mobile):
                        </label>
                        <input type="text" class="form-control form-control-lg fs-6" id="username" name="username" placeholder="e.g. HWH0095, admin, Sr. DEE(OP)/HWH, TLC, PCNL, 9876543210" required autofocus>
                        <div class="form-text small">
                            <strong class="text-primary">CLIs:</strong> Enter your designated <strong>CLI ID (e.g. HWH0095, HWH0097)</strong> &bull; <strong class="text-success">Crew:</strong> CMS ID or Mobile &bull; <strong class="text-danger">Admin:</strong> admin.
                        </div>'''

html = html.replace(old_input, new_input)

# Update Level 2 CLI row in table
old_cli_row = '''                                    <td>
                                        <strong>CLI Login</strong><br>
                                        <small class="text-muted">Chief Loco Inspector & CCC</small>
                                    </td>
                                    <td><code>CLI_HWH_01</code> / <code>CCC_HWH</code></td>'''

new_cli_row = '''                                    <td>
                                        <strong>CLI Login</strong><br>
                                        <small class="text-muted">Chief Loco Inspector & CCC</small>
                                    </td>
                                    <td><code>HWH0095</code> (CLI ID)<br><code>CLI_HWH_01</code> / <code>CCC_HWH</code></td>'''

html = html.replace(old_cli_row, new_cli_row)

with open(login_file, 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated templates/auth/login.html successfully.")
