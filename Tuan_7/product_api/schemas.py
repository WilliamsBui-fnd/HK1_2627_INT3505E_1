from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class ProductOut(Schema):
    id = fields.Int()
    sku = fields.Str()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    price_cents = fields.Int()
    qty_in_stock = fields.Int()
    archived = fields.Bool()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class ProductIn(Schema):
    sku = fields.Str(required=True, validate=[validate.Length(min=3, max=32), validate.Regexp(r"^[A-Z0-9-]+$")])
    name = fields.Str(required=True, validate=[validate.Length(min=1, max=255), validate.Regexp(r".*\S.*")])
    description = fields.Str(allow_none=True, validate=validate.Length(max=2000))
    price_cents = fields.Int(required=True, strict=True, validate=validate.Range(min=0))
    qty_in_stock = fields.Int(load_default=0, strict=True, validate=validate.Range(min=0))


class ProductPatch(Schema):
    name = fields.Str(validate=[validate.Length(min=1, max=255), validate.Regexp(r".*\S.*")])
    description = fields.Str(allow_none=True, validate=validate.Length(max=2000))
    price_cents = fields.Int(strict=True, validate=validate.Range(min=0))
    qty_in_stock = fields.Int(strict=True, validate=validate.Range(min=0))


class ReserveIn(Schema):
    qty = fields.Int(required=True, strict=True, validate=validate.Range(min=1))


class OrderItemIn(Schema):
    product_id = fields.Int(required=True, strict=True, validate=validate.Range(min=1))
    qty = fields.Int(required=True, strict=True, validate=validate.Range(min=1))


class OrderIn(Schema):
    items = fields.List(fields.Nested(OrderItemIn), required=True, validate=validate.Length(min=1))

    @validates_schema
    def unique_products(self, data, **kwargs):
        ids = [item["product_id"] for item in data["items"]]
        if len(ids) != len(set(ids)):
            raise ValidationError("product_id must be unique within an order", field_name="items")


class OrderItemOut(Schema):
    id = fields.Int()
    product_id = fields.Int()
    qty = fields.Int()
    unit_price_cents = fields.Int()
    line_total_cents = fields.Method("line_total")
    product_name = fields.Method("name")

    def line_total(self, obj):
        return obj.qty * obj.unit_price_cents

    def name(self, obj):
        return obj.product.name


class OrderOut(Schema):
    id = fields.Int()
    created_at = fields.DateTime()
    items = fields.List(fields.Nested(OrderItemOut))
    total_cents = fields.Method("total")

    def total(self, obj):
        return sum(item.qty * item.unit_price_cents for item in obj.items)
