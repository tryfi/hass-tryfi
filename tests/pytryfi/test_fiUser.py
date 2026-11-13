from custom_components.tryfi.pytryfi.fiUser import FiUser


def test_fi_user_init_details_and_properties():
    user = FiUser("user123")
    assert user.userId == "user123"

    details = {
        "email": "user@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "phoneNumber": "555-1234",
    }
    user.setUserDetails(details)

    assert user.userId == "user123"
    assert user.email == "user@example.com"
    assert user.firstName == "John"
    assert user.lastName == "Doe"
    assert user.phoneNumber == "555-1234"
    assert user.fullName == "John Doe"
    assert user.lastUpdated is not None
    assert str(user) == "User ID: user123 Name: John Doe Email: user@example.com"
