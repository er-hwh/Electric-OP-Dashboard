path = r'c:\Users\Indian Railway\Desktop\Electric OP Dashboard\blueprints\duty_hours.py'

with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    """return jsonify({'detail': "Please upload a valid Excel file (.xlsx or .xls}), 400.")""",
    """return jsonify({'detail': "Please upload a valid Excel file (.xlsx or .xls)."}), 400"""
)

text = text.replace(
    """return jsonify({'detail': str(e}), 400)""",
    """return jsonify({'detail': str(e)}), 400"""
)

text = text.replace(
    """return jsonify({'detail': f"Database truncation error: {str(e}), 500}")""",
    """return jsonify({'detail': f"Database truncation error: {str(e)}"}), 500"""
)

text = text.replace(
    """return jsonify({'detail': f"Database write error: {str(e}), 500}")""",
    """return jsonify({'detail': f"Database write error: {str(e)}"}), 500"""
)

text = text.replace(
    """return jsonify({'detail': f"Error generating route-wise summary Excel: {str(e}), 500}")""",
    """return jsonify({'detail': f"Error generating route-wise summary Excel: {str(e)}"}), 500"""
)

text = text.replace(
    """return jsonify({'detail': f"Error generating dates summary Excel: {str(e}), 500}")""",
    """return jsonify({'detail': f"Error generating dates summary Excel: {str(e)}"}), 500"""
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

print('Syntax fixed successfully!')
