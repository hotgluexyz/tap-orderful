"""Stream type classes for tap-orderful."""

from typing import Iterable, Iterator, Optional

from hotglue_singer_sdk import typing as th

from tap_orderful.client import OrderfulStream


class TransactionsStream(OrderfulStream):
    """Transactions stream - metadata index for all EDI documents exchanged via Orderful."""

    name = "transactions"
    path = "transactions"

    def get_child_context(self, record: dict, context: Optional[dict] = None) -> dict:
        """Pass transaction_id and edi_type to typed child streams."""
        return {
            "transaction_id": record["id"],
            "edi_type": record.get("type", {}).get("name", ""),
        }

    _party_schema = th.ObjectType(
        th.Property("isaId", th.StringType),
        th.Property("isaIdQualifier", th.StringType),
        th.Property("testIsaId", th.StringType),
        th.Property("testIsaIdQualifier", th.StringType),
        th.Property("name", th.StringType),
    )

    _ref_id_schema = th.ObjectType(
        th.Property("value", th.StringType),
        th.Property("type", th.StringType),
        th.Property("owner", th.StringType),
    )

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("href", th.StringType),
        th.Property("version", th.StringType),
        th.Property("sender", _party_schema),
        th.Property("receiver", _party_schema),
        th.Property(
            "type",
            th.ObjectType(th.Property("name", th.StringType)),
        ),
        th.Property("stream", th.StringType),
        th.Property("businessNumber", th.StringType),
        th.Property("referenceIdentifiers", th.ArrayType(_ref_id_schema)),
        th.Property(
            "message",
            th.ObjectType(th.Property("href", th.StringType)),
        ),
        th.Property("validationStatus", th.StringType),
        th.Property("deliveryStatus", th.StringType),
        th.Property("acknowledgmentStatus", th.StringType),
        th.Property("createdAt", th.DateTimeType),
        th.Property("lastUpdatedAt", th.DateTimeType),
        th.Property(
            "acknowledgment",
            th.ObjectType(th.Property("href", th.StringType)),
        ),
    ).to_dict()


class EdiMessageStream(OrderfulStream):
    """Base class for typed EDI message streams (children of TransactionsStream).

    Subclasses must set `edi_type` to the Orderful transaction type name they handle
    (e.g. "850_PURCHASE_ORDER"). Records for other types are skipped without an
    HTTP call so the parent scan is never multiplied across child streams.
    """

    edi_type: str = ""
    path = "transactions/{transaction_id}/message"
    parent_stream_type = TransactionsStream
    primary_keys = ["transaction_id"]
    replication_key = None

    # EDI envelope segments stripped from the record output
    _ENVELOPE_KEYS = {"transactionSetHeader", "transactionSetTrailer"}

    def get_context_state(self, context: Optional[dict]) -> dict:
        """Use stream-level state to avoid one partition entry per transaction_id."""
        return self.stream_state

    def get_records(self, context: Optional[dict]) -> Iterator[dict]:
        """Skip the HTTP call entirely when the parent type does not match."""
        if context and context.get("edi_type") != self.edi_type:
            return
        yield from super().get_records(context)

    def parse_response(self, response) -> Iterable[dict]:
        """Yield one record: transaction_id + flattened transactionSets body."""
        data = response.json()
        txn_id = response.url.split("/transactions/")[1].split("/")[0]
        body = (data.get("transactionSets") or [{}])[0]
        record = {"transaction_id": txn_id}
        record.update(
            {k: v for k, v in body.items() if k not in self._ENVELOPE_KEYS}
        )
        yield record


# ── Shared sub-schemas ──────────────────────────────────────────────────────
_party_loop = th.ArrayType(
    th.ObjectType(
        th.Property(
            "partyIdentification",
            th.ArrayType(
                th.ObjectType(
                    th.Property("entityIdentifierCode", th.StringType),
                    th.Property("name", th.StringType),
                    th.Property("identificationCodeQualifier", th.StringType),
                    th.Property("identificationCode", th.StringType),
                )
            ),
        ),
        th.Property(
            "partyLocation",
            th.ArrayType(
                th.ObjectType(th.Property("addressInformation", th.StringType))
            ),
        ),
        th.Property(
            "geographicLocation",
            th.ArrayType(
                th.ObjectType(
                    th.Property("cityName", th.StringType),
                    th.Property("stateOrProvinceCode", th.StringType),
                    th.Property("postalCode", th.StringType),
                    th.Property("countryCode", th.StringType),
                )
            ),
        ),
    )
)

_date_ref = th.ArrayType(
    th.ObjectType(
        th.Property("dateTimeQualifier", th.StringType),
        th.Property("date", th.StringType),
        th.Property("time", th.StringType),
    )
)

_ref_info = th.ArrayType(
    th.ObjectType(
        th.Property("referenceIdentificationQualifier", th.StringType),
        th.Property("referenceIdentification", th.StringType),
    )
)

_terms = th.ArrayType(
    th.ObjectType(
        th.Property("termsTypeCode", th.StringType),
        th.Property("termsBasisDateCode", th.StringType),
        th.Property("termsDiscountPercent", th.StringType),
        th.Property("termsDiscountDaysDue", th.StringType),
        th.Property("description", th.StringType),
    )
)

_product_id_fields = [
    th.Property("productServiceIDQualifier", th.StringType),
    th.Property("productServiceID", th.StringType),
    th.Property("productServiceIDQualifier1", th.StringType),
    th.Property("productServiceID1", th.StringType),
    th.Property("productServiceIDQualifier2", th.StringType),
    th.Property("productServiceID2", th.StringType),
    th.Property("productServiceIDQualifier3", th.StringType),
    th.Property("productServiceID3", th.StringType),
    th.Property("productServiceIDQualifier4", th.StringType),
    th.Property("productServiceID4", th.StringType),
    th.Property("productServiceIDQualifier5", th.StringType),
    th.Property("productServiceID5", th.StringType),
]


# ── 850 Purchase Order ───────────────────────────────────────────────────────
class PurchaseOrdersStream(EdiMessageStream):
    """Purchase orders stream - inbound EDI 850 documents (suppliers → org)."""

    name = "purchase_orders"
    edi_type = "850_PURCHASE_ORDER"

    schema = th.PropertiesList(
        th.Property("transaction_id", th.StringType),
        th.Property(
            "beginningSegmentForPurchaseOrder",
            th.ArrayType(
                th.ObjectType(
                    th.Property("transactionSetPurposeCode", th.StringType),
                    th.Property("purchaseOrderTypeCode", th.StringType),
                    th.Property("purchaseOrderNumber", th.StringType),
                    th.Property("date", th.StringType),
                )
            ),
        ),
        th.Property("referenceInformation", _ref_info),
        th.Property("dateTimeReference", _date_ref),
        th.Property("termsOfSaleDeferredTermsOfSale", _terms),
        th.Property(
            "FOBRelatedInstructions",
            th.ArrayType(
                th.ObjectType(th.Property("shipmentMethodOfPaymentCode", th.StringType))
            ),
        ),
        th.Property(
            "salesRequirements",
            th.ArrayType(
                th.ObjectType(th.Property("salesRequirementCode", th.StringType))
            ),
        ),
        th.Property(
            "carrierDetailsRoutingSequenceTransitTime",
            th.ArrayType(th.ObjectType(th.Property("routing", th.StringType))),
        ),
        th.Property("N1_loop", _party_loop),
        th.Property(
            "PO1_loop",
            th.ArrayType(
                th.ObjectType(
                    th.Property(
                        "baselineItemData",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property("assignedIdentification", th.StringType),
                                th.Property("quantity", th.StringType),
                                th.Property("unitOrBasisForMeasurementCode", th.StringType),
                                th.Property("unitPrice", th.StringType),
                                *_product_id_fields,
                            )
                        ),
                    ),
                    th.Property(
                        "PID_loop",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property(
                                    "productItemDescription",
                                    th.ArrayType(
                                        th.ObjectType(
                                            th.Property("itemDescriptionTypeCode", th.StringType),
                                            th.Property("productProcessCharacteristicCode", th.StringType),
                                            th.Property("description", th.StringType),
                                        )
                                    ),
                                )
                            )
                        ),
                    ),
                    th.Property(
                        "itemPhysicalDetails",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property("pack", th.StringType),
                                th.Property("innerPack", th.StringType),
                            )
                        ),
                    ),
                )
            ),
        ),
        th.Property(
            "SAC_loop",
            th.ArrayType(
                th.ObjectType(
                    th.Property(
                        "servicePromotionAllowanceOrChargeInformation",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property("allowanceOrChargeIndicatorCode", th.StringType),
                                th.Property("servicePromotionAllowanceOrChargeCode", th.StringType),
                                th.Property("amount", th.StringType),
                                th.Property("allowanceChargePercentQualifier", th.StringType),
                                th.Property("description", th.StringType),
                            )
                        ),
                    )
                )
            ),
        ),
        th.Property(
            "CTT_loop",
            th.ArrayType(
                th.ObjectType(
                    th.Property(
                        "transactionTotals",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property("numberOfLineItems", th.StringType),
                                th.Property("hashTotal", th.StringType),
                            )
                        ),
                    )
                )
            ),
        ),
    ).to_dict()


# ── 855 PO Acknowledgment ────────────────────────────────────────────────────
class PoAcknowledgmentsStream(EdiMessageStream):
    """PO acknowledgments stream - EDI 855 documents (org → buyer or supplier → org)."""

    name = "po_acknowledgments"
    edi_type = "855_PURCHASE_ORDER_ACKNOWLEDGMENT"

    schema = th.PropertiesList(
        th.Property("transaction_id", th.StringType),
        th.Property(
            "beginningSegmentForPurchaseOrderAcknowledgment",
            th.ArrayType(
                th.ObjectType(
                    th.Property("purchaseOrderNumber", th.StringType),
                    th.Property("purchaseOrderAcknowledgmentNumber", th.StringType),
                    th.Property("acknowledgmentTypeCode", th.StringType),
                    th.Property("date", th.StringType),
                )
            ),
        ),
        th.Property("referenceInformation", _ref_info),
        th.Property("dateTimeReference", _date_ref),
        th.Property("N1_loop", _party_loop),
        th.Property(
            "PO1_loop",
            th.ArrayType(
                th.ObjectType(
                    th.Property(
                        "baselineItemData",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property("assignedIdentification", th.StringType),
                                th.Property("quantity", th.StringType),
                                th.Property("unitOrBasisForMeasurementCode", th.StringType),
                                th.Property("unitPrice", th.StringType),
                                *_product_id_fields,
                            )
                        ),
                    ),
                    th.Property(
                        "lineItemAcknowledgment",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property("lineItemStatusCode", th.StringType),
                                th.Property("quantity", th.StringType),
                                th.Property("unitOrBasisForMeasurementCode", th.StringType),
                            )
                        ),
                    ),
                )
            ),
        ),
        th.Property(
            "CTT_loop",
            th.ArrayType(
                th.ObjectType(
                    th.Property(
                        "transactionTotals",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property("numberOfLineItems", th.StringType),
                                th.Property("hashTotal", th.StringType),
                            )
                        ),
                    )
                )
            ),
        ),
    ).to_dict()


# ── 856 Ship Notice / Manifest ───────────────────────────────────────────────
class ShipNoticesStream(EdiMessageStream):
    """Ship notices stream - EDI 856 ASN documents (org → buyer)."""

    name = "ship_notices"
    edi_type = "856_SHIP_NOTICE_MANIFEST"

    # The HL_loop is a flat array of nodes in a shipment/order/pack/item hierarchy.
    # Each node's available segments depend on its hierarchicalLevelCode (S/O/P/I),
    # so we type it as an array of open objects rather than trying to enumerate all paths.
    _hl_node = th.ObjectType(
        th.Property(
            "hierarchicalLevel",
            th.ArrayType(
                th.ObjectType(
                    th.Property("hierarchicalIDNumber", th.StringType),
                    th.Property("hierarchicalParentIDNumber", th.StringType),
                    th.Property("hierarchicalLevelCode", th.StringType),
                )
            ),
        ),
        th.Property("referenceInformation", _ref_info),
        th.Property("dateTimeReference", _date_ref),
        th.Property("N1_loop", _party_loop),
        th.Property(
            "purchaseOrderReference",
            th.ArrayType(
                th.ObjectType(th.Property("purchaseOrderNumber", th.StringType))
            ),
        ),
        th.Property(
            "marksAndNumbersInformation",
            th.ArrayType(
                th.ObjectType(
                    th.Property("marksAndNumbersQualifier", th.StringType),
                    th.Property("marksAndNumbers", th.StringType),
                )
            ),
        ),
        th.Property(
            "itemIdentification",
            th.ArrayType(
                th.ObjectType(*_product_id_fields)
            ),
        ),
        th.Property(
            "itemDetailShipment",
            th.ArrayType(
                th.ObjectType(
                    th.Property("numberOfUnitsShipped", th.StringType),
                    th.Property("unitOrBasisForMeasurementCode", th.StringType),
                )
            ),
        ),
        th.Property(
            "carrierDetailsRoutingSequenceTransitTime",
            th.ArrayType(
                th.ObjectType(
                    th.Property("transportationMethodTypeCode", th.StringType),
                    th.Property("routingSequenceCode", th.StringType),
                )
            ),
        ),
    )

    schema = th.PropertiesList(
        th.Property("transaction_id", th.StringType),
        th.Property(
            "beginningSegmentForShipNotice",
            th.ArrayType(
                th.ObjectType(
                    th.Property("shipmentIdentification", th.StringType),
                    th.Property("date", th.StringType),
                    th.Property("time", th.StringType),
                    th.Property("hierarchicalStructureCode", th.StringType),
                    th.Property("purpose", th.StringType),
                )
            ),
        ),
        th.Property("HL_loop", th.ArrayType(_hl_node)),
    ).to_dict()


# ── 810 Invoice ──────────────────────────────────────────────────────────────
class InvoicesStream(EdiMessageStream):
    """Invoices stream - EDI 810 documents (org → buyer or supplier → org)."""

    name = "invoices"
    edi_type = "810_INVOICE"

    schema = th.PropertiesList(
        th.Property("transaction_id", th.StringType),
        th.Property(
            "beginningSegmentForInvoice",
            th.ArrayType(
                th.ObjectType(
                    th.Property("invoiceNumber", th.StringType),
                    th.Property("date", th.StringType),
                    th.Property("purchaseOrderNumber", th.StringType),
                    th.Property("transactionTypeCode", th.StringType),
                )
            ),
        ),
        th.Property("referenceInformation", _ref_info),
        th.Property("dateTimeReference", _date_ref),
        th.Property("termsOfSaleDeferredTermsOfSale", _terms),
        th.Property("N1_loop", _party_loop),
        th.Property(
            "IT1_loop",
            th.ArrayType(
                th.ObjectType(
                    th.Property(
                        "baselineItemDataInvoice",
                        th.ArrayType(
                            th.ObjectType(
                                th.Property("assignedIdentification", th.StringType),
                                th.Property("quantityInvoiced", th.StringType),
                                th.Property("unitOrBasisForMeasurementCode", th.StringType),
                                th.Property("unitPrice", th.StringType),
                                *_product_id_fields,
                            )
                        ),
                    ),
                )
            ),
        ),
        th.Property(
            "totalMonetaryValueSummary",
            th.ArrayType(
                th.ObjectType(
                    th.Property("amount", th.StringType),
                    th.Property("amount1", th.StringType),
                )
            ),
        ),
        th.Property(
            "transactionTotals",
            th.ArrayType(
                th.ObjectType(th.Property("numberOfLineItems", th.StringType))
            ),
        ),
    ).to_dict()


# ── Supporting streams ───────────────────────────────────────────────────────
class RelationshipsStream(OrderfulStream):
    """Relationships stream - trading partner relationships configured in Orderful."""

    name = "relationships"
    path = "relationships"
    replication_key = "updatedAt"

    _party_schema = th.ObjectType(
        th.Property("ediAccountId", th.IntegerType),
        th.Property("liveIsaId", th.StringType),
        th.Property("testIsaId", th.StringType),
        th.Property("organizationName", th.StringType),
        th.Property("ediAccountName", th.StringType),
        th.Property("organizationId", th.IntegerType),
    )

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("createdAt", th.DateTimeType),
        th.Property("updatedAt", th.DateTimeType),
        th.Property("sender", _party_schema),
        th.Property("receiver", _party_schema),
        th.Property(
            "transactionType",
            th.ObjectType(th.Property("name", th.StringType)),
        ),
        th.Property("status", th.StringType),
        th.Property("autoSend", th.StringType),
    ).to_dict()


class OrganizationStream(OrderfulStream):
    """Organization stream - current user's organization details (singleton)."""

    name = "organization"
    path = "organizations/me"
    primary_keys = ["id"]
    replication_key = None

    def parse_response(self, response) -> Iterable[dict]:
        """Yield the single organization object."""
        yield response.json()

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("name", th.StringType),
        th.Property(
            "ediAccounts",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.StringType),
                    th.Property("name", th.StringType),
                    th.Property("liveIsaId", th.StringType),
                    th.Property("testIsaId", th.StringType),
                )
            ),
        ),
    ).to_dict()
