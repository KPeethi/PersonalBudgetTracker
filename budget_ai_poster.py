from PIL import Image, ImageDraw, ImageFont
import os
import sys

def create_poster():
    # Create a new image with a blue background
    width, height = 1000, 1200
    poster = Image.new('RGB', (width, height), (26, 58, 95))  # Dark blue background
    draw = ImageDraw.Draw(poster)
    
    try:
        # Try to load fonts (these will fall back to default if not available)
        title_font = ImageFont.truetype("arial.ttf", 60)
        subtitle_font = ImageFont.truetype("arial.ttf", 24)
        section_font = ImageFont.truetype("arial.ttf", 28)
        text_font = ImageFont.truetype("arial.ttf", 18)
    except IOError:
        # Fall back to default font
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        section_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Title
    draw.text((width//2, 50), "Budget AI", fill=(248, 209, 108), font=title_font, anchor="mm")
    draw.text((width//2, 100), "Transform your financial tracking with intelligent insights", 
              fill=(240, 248, 255), font=subtitle_font, anchor="mm")
    
    # Load screenshots if available
    screenshots = []
    screenshot_paths = [
        "attached_assets/image_1744761066643.png",  # Dashboard
        "attached_assets/image_1744761082579.png",  # Analytics
        "attached_assets/image_1744761098785.png",  # Expenses
        "attached_assets/image_1744761070198.png",  # Bank Integration
    ]
    
    for path in screenshot_paths:
        if os.path.exists(path):
            try:
                img = Image.open(path)
                # Resize while maintaining aspect ratio
                base_width = 400
                w_percent = base_width / float(img.width)
                h_size = int(float(img.height) * float(w_percent))
                img = img.resize((base_width, h_size), Image.LANCZOS)
                screenshots.append(img)
            except Exception as e:
                print(f"Error loading image {path}: {e}")
                # Create a placeholder
                placeholder = Image.new('RGB', (400, 250), (70, 100, 150))
                placeholder_draw = ImageDraw.Draw(placeholder)
                placeholder_draw.text((200, 125), f"Screenshot {len(screenshots)+1}", 
                                     fill=(240, 248, 255), font=text_font, anchor="mm")
                screenshots.append(placeholder)
        else:
            # Create a placeholder
            placeholder = Image.new('RGB', (400, 250), (70, 100, 150))
            placeholder_draw = ImageDraw.Draw(placeholder)
            placeholder_draw.text((200, 125), f"Screenshot {len(screenshots)+1}", 
                                 fill=(240, 248, 255), font=text_font, anchor="mm")
            screenshots.append(placeholder)
    
    # Features section
    draw.rectangle([(50, 150), (width-50, 280)], fill=(35, 75, 112), outline=(76, 163, 255), width=2)
    draw.text((70, 170), "Key Features", fill=(248, 209, 108), font=section_font)
    
    features = [
        "• Smart Visualizations", "• AI-Powered Analysis", "• Bank Integration",
        "• Responsive Design", "• Business Features", "• Excel Import"
    ]
    
    # Draw features in two rows
    for i, feature in enumerate(features[:3]):
        draw.text((70 + i*300, 210), feature, fill=(240, 248, 255), font=text_font)
    for i, feature in enumerate(features[3:]):
        draw.text((70 + i*300, 240), feature, fill=(240, 248, 255), font=text_font)
    
    # Place screenshots
    screenshot_titles = ["Intuitive Dashboard", "Advanced Analytics", 
                         "Expense Management", "Bank Integration"]
    screenshot_descriptions = [
        "Track spending patterns and visualize financial trends at a glance.",
        "Dive deep into your spending habits with sophisticated analytics.",
        "Effortlessly track and categorize expenses with our clean interface.",
        "Connect securely to your accounts for automated transaction tracking."
    ]
    
    for i, (img, title, desc) in enumerate(zip(screenshots, screenshot_titles, screenshot_descriptions)):
        # Calculate position (2x2 grid)
        row = i // 2
        col = i % 2
        x = 70 + col * 450
        y = 300 + row * 330
        
        # Draw section background
        draw.rectangle([(x-20, y-20), (x+400+20, y+250+70)], 
                      fill=(35, 75, 112), outline=(76, 163, 255), width=1)
        
        # Draw title
        draw.text((x, y-10), title, fill=(248, 209, 108), font=section_font)
        
        # Paste screenshot
        poster.paste(img, (x, y+30))
        
        # Draw description
        # Wrap text - simple implementation
        words = desc.split()
        line = ""
        y_text = y + img.height + 40
        for word in words:
            test_line = line + word + " "
            line_width = draw.textlength(test_line, font=text_font)
            if line_width < 390:
                line = test_line
            else:
                draw.text((x, y_text), line, fill=(240, 248, 255), font=text_font)
                y_text += text_font.size + 5
                line = word + " "
        draw.text((x, y_text), line, fill=(240, 248, 255), font=text_font)
    
    # Footer
    draw.line([(50, height-200), (width-50, height-200)], fill=(76, 163, 255), width=2)
    
    # QR code placeholder
    draw.rectangle([(70, height-180), (270, height-30)], fill=(255, 255, 255), outline=(240, 248, 255), width=1)
    draw.rectangle([(100, height-150), (240, height-60)], fill=(0, 0, 0))
    draw.rectangle([(120, height-130), (220, height-80)], fill=(255, 255, 255))
    draw.text((170, height-20), "Scan to download", fill=(240, 248, 255), font=text_font, anchor="mm")
    draw.text((170, height-190), "Try Budget AI Today", fill=(248, 209, 108), font=section_font, anchor="mm")
    
    # Contact information
    draw.text((width-170, height-180), "Contact Us", fill=(248, 209, 108), font=section_font, anchor="mm")
    contact_info = [
        "Email: info@budgetai.com",
        "Web: www.budgetai.com",
        "Phone: (555) 123-4567"
    ]
    for i, line in enumerate(contact_info):
        draw.text((width-170, height-140 + i*30), line, fill=(240, 248, 255), font=text_font, anchor="mm")
    
    # Save the poster
    poster.save("budget_ai_poster.png")
    print("Poster created successfully: budget_ai_poster.png")

if __name__ == "__main__":
    create_poster()