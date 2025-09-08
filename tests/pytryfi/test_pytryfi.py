import responses
from custom_components.tryfi.pytryfi import PyTryFi
from tests.pytryfi.utils import (
    GRAPHQL_PARTIAL_PET,
    mock_household_with_pets,
    mock_login_requests,
)


@responses.activate
def test_pet_with_no_collar():
    mock_login_requests()

    mock_household_with_pets(
        pets=[
            {
                "__typename": "Pet",
                "id": "testpetwithnodevice",
                "chip": None,
                "name": "Yolo",
                "device": None,
            }
        ]
    )

    tryfi = PyTryFi()

    assert tryfi.pets == []


@responses.activate
def test_generic_init():
    mock_login_requests()
    mock_household_with_pets(
        pets=[
            GRAPHQL_PARTIAL_PET
        ]
    )

    tryfi = PyTryFi()

    assert len(tryfi.pets) == 1

    assert tryfi.pets[0].petId == "test-pet"
