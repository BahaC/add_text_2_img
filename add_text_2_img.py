from PIL import Image, ImageDraw, ImageFont
import os
import torch
import numpy as np


class AddText:
    """
    Node for adding text to an image
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        # Get the font directory and all font files
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(script_dir, "fonts")
        available_fonts = ["Custom"] + \
                          [f[:-4] for f in os.listdir(font_dir) if
                           f.endswith(".ttf") | f.endswith(".TTF") | f.endswith(".ttc")]
        available_fonts = list(set(available_fonts))  # Deduplication

        return {
            "required": {
                "image": ("IMAGE",),
                "text": ("STRING", {"multiline": True, "default": "A cute puppy"}),
                "x": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 1, "display": "number"}),
                "y": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 1, "display": "number"}),
                "font_size": ("INT", {"default": 38, "min": 0, "max": 1000, "step": 1, "display": "number"}),
                "font_family": (available_fonts,),
                "font_color": ("STRING", {"multiline": False, "default": "#ffffff"}),
                "font_shadow_x": ("INT", {"default": 0, "min": 0, "max": 20, "step": 1, "display": "number"}),
                "font_shadow_y": ("INT", {"default": 0, "min": 0, "max": 20, "step": 1, "display": "number"}),
                "shadow_color": ("STRING", {"multiline": False, "default": "#000000"}),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0, "max": 1.0, "step": 0.1, "display": "number"}),
                "rotation": ("INT", {"default": 0, "min": 0, "max": 360, "step": 5, "display": "number"}),


            },
            "optional": {
                "custom_font_path": ("STRING", {"multiline": False, "default": "",
                                                "visible_if": {"font_family": "Custom"}}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "add_text"
    CATEGORY = "AI_Boy"

    def add_text(self, image, text, x, y, font_size, font_family, font_color, font_shadow_x, font_shadow_y,
                 shadow_color, opacity, rotation, custom_font_path=None):
        """
        Add text to images
        """

        # Get the dimension information of the original image
        orig_shape = image.shape

        # Adjust the order of dimensions
        image = image.permute(0, 3, 1, 2)

        # Setting the font
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(script_dir, "fonts")

        # Resolving font paths
        font_path = parse_font_path(font_family, custom_font_path, font_dir)
        font = ImageFont.truetype(font_path, font_size)

        # Parsing color values
        font_color = parse_font_color(font_color)
        shadow_color = parse_font_color(shadow_color)

        # Convert Tensor to PIL Image
        images = []
        for i in range(image.shape[0]):
            img = torch.clamp(image[i], min=0., max=1.)
            img = (img * 255).cpu().numpy().astype(np.uint8)
            img = Image.fromarray(img.transpose(1, 2, 0)).convert("RGB")
            images.append(img)

        processed_images = []
        for img in images:
            # Get the width and height of an image
            image_width, image_height = img.size
            # Check if x, y is out of range, if so clamp it to the image range
            x = max(0, min(x, image_width - 1))
            y = max(0, min(y, image_height - 1))

            # Get the width and height of the text
            text_width, text_height = font.getmask(text).size

            # If x, y are not set, the default text is centered just below the image.
            if x == 0 and y == 0:
                # Calculate the x coordinate of the text to center it horizontally
                x = (image_width - text_width) // 2
                # Calculate the y coordinate of the text so that it is directly below the image
                y = image_height - 50  # Add 50 pixels of spacing

            # Creating a drawing object
            background = Image.new("RGBA", (image_width, image_height), (255, 255, 255, 0))

            draw = ImageDraw.Draw(background)
            
            alpha = opacity * 255
            alpha = int(alpha)
            rgba_color = (*font_color, alpha)

            background_2 = Image.new("RGBA", (text_width, text_height + font_shadow_y + 30), (255, 255, 255, 0))
            draw_2 = ImageDraw.Draw(background_2)

            if font_shadow_x > 0 and font_shadow_y > 0:
                draw_2.text((font_shadow_x, font_shadow_y), text, font=font, fill=shadow_color)
            # Add text
            draw_2.text((0, 0), text, font=font, fill=rgba_color)

            background_2 = background_2.rotate(rotation, expand=True)            

            background.paste(background_2, (x,y))
            img = Image.alpha_composite(img.convert("RGBA"), background).convert("RGB")

            processed_images.append(img)

        # Convert PIL Image back to Tensor
        processed_images = [np.array(img).astype(np.float32) / 255.0 for img in processed_images]
        image = torch.from_numpy(np.stack(processed_images, axis=0))

        # Restore the original image dimension order
        image = image.reshape(orig_shape)
        return (image,)


NODE_CLASS_MAPPINGS = {
    "AddText": AddText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AddText": "AddTextToImage",
}


# Parsing color values
def parse_font_color(font_color):
    if font_color.startswith("#"):
        font_color = font_color.lstrip('#')
        try:
            font_color = tuple(int(font_color[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            raise ValueError("Invalid hexadecimal color value: {}".format(font_color))
    else:
        try:
            font_color = tuple(map(int, font_color.split(',')))
            if len(font_color) != 3:
                raise ValueError("RGB color values ​​must contain three integers")
        except ValueError:
            raise ValueError("Invalid RGB color value: {}".format(font_color))
    return font_color


# Resolving font paths
def parse_font_path(font_family, custom_font_path, font_dir):
    if font_family == "Custom":
        if not os.path.exists(custom_font_path):
            raise ValueError(f"The custom font path does not exist: {custom_font_path}")
        font_path = custom_font_path
    else:
        font_path = os.path.join(font_dir, f"{font_family}.ttf")
        if not os.path.exists(font_path):
            font_path = os.path.join(font_dir, f"{font_family}.TTF")
        # If the .ttf file does not exist, the .ttc file is tried
        if not os.path.exists(font_path):
            font_path = os.path.join(font_dir, f"{font_family}.ttc")
        if not os.path.exists(font_path):
            font_path = os.path.join(font_dir, f"{font_family}.TTC")
    # Check if the font file exists
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return font_path
