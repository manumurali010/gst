# Letterhead Templates Guide

## Overview
This folder contains letterhead templates used in the GST Adjudication System. You can customize these templates or create your own to match your office's branding and requirements.

## Template Requirements

### Required Elements
Every letterhead template **MUST** include the following HTML elements:

1. **Form Header Placeholder**
   ```html
   <div id="form-header-placeholder">
   </div>
   ```
   This is where form-specific headers (like "FORM GST DRC-01A") will be injected.

2. **Content Placeholder** (Optional but recommended)
   ```html
   <div id="content-placeholder">
   </div>
   ```
   This is where additional form content may be placed.

### Basic Structure
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        /* Your custom CSS here */
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        /* Add more styles as needed */
    </style>
</head>
<body>
    <!-- Your letterhead design -->
    <div class="header">
        <h1>Your Office Name</h1>
        <p>Address and Contact Information</p>
    </div>
    
    <!-- REQUIRED: Form header placeholder -->
    <div id="form-header-placeholder">
    </div>
    
    <!-- OPTIONAL: Content placeholder -->
    <div id="content-placeholder">
    </div>
</body>
</html>
```

## Customization Tips

### 1. Adding Your Logo
```html
<div class="header">
    <img src="path/to/logo.png" alt="Logo" style="height: 80px;">
    <h1>Your Office Name</h1>
</div>
```

### 2. Custom Colors and Fonts
```css
<style>
    :root {
        --primary-color: #2c3e50;
        --secondary-color: #3498db;
    }
    
    body {
        font-family: 'Times New Roman', serif;
        color: var(--primary-color);
    }
    
    .header {
        background-color: var(--secondary-color);
        color: white;
        padding: 20px;
    }
</style>
```

### 3. Office-Specific Information
You can hardcode your office details in the template:
```html
<div class="office-info">
    <p><strong>Office:</strong> GST Department - Paravur Range</p>
    <p><strong>Jurisdiction:</strong> Kerala</p>
    <p><strong>Phone:</strong> +91-XXX-XXXXXXX</p>
    <p><strong>Email:</strong> gst.paravur@gov.in</p>
</div>
```

## How to Use Custom Letterheads

### Method 1: Through Settings Dialog
1. Open the application
2. Click "Settings" in the top menu
3. Go to the "Letterhead" tab
4. Click "Upload Custom Letterhead"
5. Select your HTML file
6. Click "Set as Default"

### Method 2: Manual Installation
1. Save your letterhead as an HTML file (e.g., `my_letterhead.html`)
2. Copy it to the `templates/letterheads/` folder
3. Open Settings and select it from the dropdown
4. Click "Set as Default"

## Included Templates

### default.html
The standard Government of India GST Department letterhead with:
- Official header
- Department emblem
- Standard formatting

### custom_example.html (if available)
An example template showing various customization options.

## Testing Your Template

1. Create your HTML file following the requirements above
2. Upload it through Settings
3. Start a new adjudication case
4. Select a form type (e.g., DRC-01A)
5. Check the preview pane to see your letterhead
6. Generate a PDF to verify the final output

## Troubleshooting

### Template Not Showing
- Ensure the file has `.html` extension
- Check that `<div id="form-header-placeholder">` exists
- Verify the file is in the `templates/letterheads/` folder

### Formatting Issues in PDF
- Keep CSS simple and inline when possible
- Avoid complex layouts or flexbox
- Use tables for structured layouts
- Test with different form types

### Upload Fails
- Check file size (should be < 1MB)
- Ensure valid HTML syntax
- Verify UTF-8 encoding

## Support

For issues or questions about letterhead customization, please contact your system administrator.
