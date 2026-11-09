import arcade
print("Attributes of arcade:")
for attr in dir(arcade):
    if "Rect" in attr or "LBWH" in attr or "XYWH" in attr:
        print(attr)
