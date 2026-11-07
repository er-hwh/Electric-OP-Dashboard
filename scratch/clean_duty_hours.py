path = r'c:\Users\Indian Railway\Desktop\Electric OP Dashboard\blueprints\duty_hours.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("""    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'detail': f\"Error reading workbook: {str(e}), 500}\")""",
"""    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'detail': f\"Error reading workbook: {str(e)}\"}), 500""")

text = text.replace("""    except HTTPException:
        raise
    except Exception as e:
        return jsonify({'detail': f\"Error filtering workbook: {str(e}), 500}\")""",
"""    except Exception as e:
        return jsonify({'detail': f\"Error filtering workbook: {str(e)}\"}), 500""")

text = text.replace("""    except HTTPException:
        raise
    except Exception as e:
        return jsonify({'detail': f\"Error generating download file: {str(e}), 500}\")""",
"""    except Exception as e:
        return jsonify({'detail': f\"Error generating download file: {str(e)}\"}), 500""")

text = text.replace('filename=f"Filtered_Continuous_Working_Hours', 'as_attachment=True, download_name=f"Filtered_Continuous_Working_Hours')

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

print('Cleaned exception blocks!')
