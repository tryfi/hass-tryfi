from custom_components.tryfi.pytryfi.ledColors import ledColors


def test_led_colors_init_and_properties():
    color = ledColors(1, "#FFFFFF", "White")
    assert color.ledColorCode == 1
    assert color.hexCode == "#FFFFFF"
    assert color.name == "White"
    assert str(color) == "Color: White Hex Code: #FFFFFF Color Code: 1"
