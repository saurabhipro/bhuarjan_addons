#!/usr/bin/env python3
"""
Script to translate msgid entries to msgstr in Hindi PO file.
This script handles both English-to-Hindi translation and copying Hindi msgid to msgstr.
"""

import re
import sys

def translate_po_file(file_path):
    """Translate the PO file by filling empty msgstr entries."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match msgid followed by msgstr ""
    pattern = r'(msgid\s+"[^"]*")\s*\nmsgstr\s+""'
    
    def replace_func(match):
        msgid_line = match.group(1)
        # Extract the content between quotes
        msgid_content = re.search(r'msgid\s+"([^"]*)"', msgid_line).group(1)
        
        # For simple cases (numbers, already Hindi text), just copy
        if (msgid_content.isdigit() or 
            msgid_content in ['%s (%s)', ''] or
            any(char in msgid_content for char in 'अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह')):
            return f'{msgid_line}\nmsgstr "{msgid_content}"'
        
        # For English text, provide Hindi translation
        translations = {
            "Aadhaar Numbers": "आधार नंबर",
            "Aadhar / आधार": "आधार",
            "Aadhar Card / आधार कार्ड": "आधार कार्ड",
            "Aadhar Number": "आधार नंबर",
            "Aadhar Number / आधार नंबर": "आधार नंबर",
            "Accept": "स्वीकार करें",
            "Accepted": "स्वीकृत",
            "Accepted / स्वीकृत": "स्वीकृत",
            "Account / खाता": "खाता",
            "Account Holder Name / खाताधारक का नाम": "खाताधारक का नाम",
            "Account Number / खाता संख्या": "खाता संख्या",
            "Acknowledge": "स्वीकार करें",
            "Acknowledged": "स्वीकृत",
            "Acknowledged / स्वीकृत": "स्वीकृत",
            "Acquired Area (Hectares) / अधिग्रहित क्षेत्रफल (हेक्टेयर)": "अधिग्रहित क्षेत्रफल (हेक्टेयर)",
            "Acquired Area (Hectares) / कुल अर्जित रकबा (हे.में.)": "कुल अर्जित रकबा (हे.में.)",
            "Acquisition Details / अधिग्रहण विवरण": "अधिग्रहण विवरण",
            "Action Needed": "कार्रवाई आवश्यक",
            "Active": "सक्रिय",
            "Add": "जोड़ें",
            "Address": "पता",
            "Administrative Approval": "प्रशासनिक अनुमोदन",
            "Age": "आयु",
            "All": "सभी",
            "Amount": "राशि",
            "Application": "आवेदन",
            "Application Date": "आवेदन तिथि",
            "Application Number": "आवेदन संख्या",
            "Approved": "अनुमोदित",
            "Area": "क्षेत्र",
            "Bank": "बैंक",
            "Bank Account": "बैंक खाता",
            "Basic Information": "मूल जानकारी",
            "Beneficiary": "लाभार्थी",
            "Cancel": "रद्द करें",
            "Category": "श्रेणी",
            "City": "शहर",
            "Close": "बंद करें",
            "Code": "कोड",
            "Comments": "टिप्पणियां",
            "Company": "कंपनी",
            "Complete": "पूर्ण",
            "Contact": "संपर्क",
            "Country": "देश",
            "Create": "बनाएं",
            "Date": "तिथि",
            "Delete": "हटाएं",
            "Description": "विवरण",
            "Details": "विवरण",
            "District": "जिला",
            "Document": "दस्तावेज",
            "Download": "डाउनलोड",
            "Edit": "संपादित करें",
            "Email": "ईमेल",
            "Error": "त्रुटि",
            "Family": "परिवार",
            "Father Name": "पिता का नाम",
            "File": "फाइल",
            "Gender": "लिंग",
            "Home": "होम",
            "ID": "आईडी",
            "Information": "जानकारी",
            "Land": "भूमि",
            "List": "सूची",
            "Location": "स्थान",
            "Login": "लॉगिन",
            "Logout": "लॉगआउट",
            "Mobile": "मोबाइल",
            "Name": "नाम",
            "New": "नया",
            "No": "नहीं",
            "Number": "संख्या",
            "OK": "ठीक है",
            "Open": "खोलें",
            "Owner": "मालिक",
            "Password": "पासवर्ड",
            "Phone": "फोन",
            "Print": "प्रिंट",
            "Profile": "प्रोफाइल",
            "Project": "परियोजना",
            "Report": "रिपोर्ट",
            "Save": "सहेजें",
            "Search": "खोजें",
            "Select": "चुनें",
            "Send": "भेजें",
            "State": "राज्य",
            "Status": "स्थिति",
            "Submit": "जमा करें",
            "Success": "सफलता",
            "Total": "कुल",
            "Type": "प्रकार",
            "Update": "अपडेट करें",
            "User": "उपयोगकर्ता",
            "View": "देखें",
            "Village": "गांव",
            "Yes": "हां",
            "Zone": "क्षेत्र"
        }
        
        # Check if we have a translation
        if msgid_content in translations:
            return f'{msgid_line}\nmsgstr "{translations[msgid_content]}"'
        else:
            # For untranslated entries, copy the msgid content
            return f'{msgid_line}\nmsgstr "{msgid_content}"'
    
    # Apply the replacement
    new_content = re.sub(pattern, replace_func, content, flags=re.MULTILINE)
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Translation completed for {file_path}")

if __name__ == "__main__":
    file_path = "/home/odoo18/odoo-source/bhuarjan_addons/bhuarjan/i18n/hi.po"
    translate_po_file(file_path)

