def test_create_product(client, auth_headers):
    payload = {
        "name": "Test Product",
        "description": "This is a valid long description",
        "price": 99.99,
        "stock": 10,
    }
    response = client.post("/products", json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["name"] == payload["name"]


def test_get_product_not_found(client, auth_headers):
    response = client.get("/products/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_and_delete_product(client, auth_headers):
    payload = {
        "name": "Test Product",
        "description": "This is a valid long description",
        "price": 99.99,
        "stock": 10,
    }
    create_res = client.post("/products", json=payload, headers=auth_headers)
    prod_id = create_res.json()["id"]

    patch_res = client.patch(
        f"/products/{prod_id}", json={"price": 149.99}, headers=auth_headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["price"] == 149.99

    del_res = client.delete(f"/products/{prod_id}", headers=auth_headers)
    assert del_res.status_code == 204
