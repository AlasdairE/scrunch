# coding: utf-8

import os
import textwrap
from StringIO import StringIO
from unittest import TestCase

from scrunch import connect
from scrunch.mutable_dataset import get_mutable_dataset


HOST = os.environ['SCRUNCH_HOST']
username = os.environ['SCRUNCH_USER']
password = os.environ['SCRUNCH_PASS']


site = connect(username, password, HOST)
assert site is not None, "Unable to connect to %s" % HOST

as_entity = lambda b: {
    "element": "shoji:entity",
    "body": b
}


class TestBackFill(TestCase):
    def _prepare_ds(self, values):
        ds = site.datasets.create(
            as_entity({"name": "test_backfill_values"})).refresh()
        # We need a numeric PK
        pk = ds.variables.create(
            as_entity(
                {
                    "name": "pk",
                    "alias": "pk",
                    "type": "numeric",
                    "values": values["pk"],
                }
            )
        )

        # Create a categorical, note the segment of -1 in rows 4, 5, 6
        cat1 = ds.variables.create(
            as_entity(
                {
                    "name": "cat1",
                    "alias": "cat1",
                    "type": "categorical",
                    "categories": [
                        {
                            "id": 1,
                            "name": "cat 1",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": 2,
                            "name": "cat 2",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": 3,
                            "name": "cat 3",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": -1,
                            "name": "No Data",
                            "missing": True,
                            "numeric_value": None,
                        },
                    ],
                    "values": values["cat1"],
                }
            )
        )

        # Create another categorical, note the segment of -1 in rows 4, 5, 6
        cat2 = ds.variables.create(
            as_entity(
                {
                    "name": "cat2",
                    "alias": "cat2",
                    "type": "categorical",
                    "categories": [
                        {
                            "id": 11,
                            "name": "cat 1",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": 22,
                            "name": "cat 2",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": 33,
                            "name": "cat 3",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": -1,
                            "name": "No Data",
                            "missing": True,
                            "numeric_value": None,
                        },
                    ],
                    "values": values["cat2"],
                }
            )
        )
        cat3 = ds.variables.create(
            as_entity(
                {
                    "name": "cat3",
                    "alias": "cat3",
                    "type": "categorical",
                    "categories": [
                        {
                            "id": 1,
                            "name": "cat 1",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": 2,
                            "name": "cat 2",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": 3,
                            "name": "cat 3",
                            "missing": False,
                            "numeric_value": None,
                        },
                        {
                            "id": -1,
                            "name": "No Data",
                            "missing": True,
                            "numeric_value": None,
                        },
                    ],
                    "values": values["cat3"],
                }
            )
        )
        return ds

    def test_backfill_values(self):
        ds = self._prepare_ds({
            "pk": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "cat1": [1, 2, 3, -1, -1, -1, 1, 2, 3, 1],
            "cat2": [11, 22, 33, -1, -1, -1, 11, 22, 33, 11],
            "cat3": [1, 2, 3, -1, -1, -1, 1, 2, 3, 1],
        })
        csv_file = StringIO(textwrap.dedent("""pk,cat1,cat2
        4,1,22
        5,2,33
        6,3,11
        """))
        scrunch_dataset = get_mutable_dataset(ds.body.id, site)

        rows_expr = "pk >= 4 and pk <=6"
        scrunch_dataset.backfill_from_csv(["cat1", "cat2"], "pk", csv_file, rows_expr)

        data = ds.follow("table", "limit=10")["data"]
        vars = ds.variables.by("alias")
        assert data[vars["cat1"]["id"]] == [1, 2, 3, 1, 2, 3, 1, 2, 3, 1]
        assert data[vars["cat2"]["id"]] == [11, 22, 33, 22, 33, 11, 11, 22, 33, 11]

        assert len(data) == 4  # Only PK and cat1 and cat2 and cat3
        assert "folder" not in ds.folders.by("type")  # Nothing of type folder

        ds.delete()

    def test_backfill_on_subvars(self):
        ds = self._prepare_ds({
            "pk": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "cat1": [1, 2, 3, -1, -1, -1, 1, 2, 3, 1],
            "cat2": [11, 22, 33, -1, -1, -1, 11, 22, 33, 11],
            "cat3": [2, 3, 1, -1, -1, -1, 2, 3, 1, 2]
        })
        vars = ds.variables.by("alias")
        array = ds.variables.create(as_entity({
            "name": "array",
            "alias": "array",
            "type": "categorical_array",
            "subvariables": [vars["cat1"].entity_url, vars["cat3"].entity_url],
        })).refresh()

        csv_file = StringIO(textwrap.dedent("""pk,cat1,cat3
                4,1,2
                5,2,3
                6,3,1
                """))
        scrunch_dataset = get_mutable_dataset(ds.body.id, site)

        rows_expr = "pk >= 4 and pk <=6"
        scrunch_dataset.backfill_from_csv(["cat1", "cat3"], "pk", csv_file,
            rows_expr)

        data = ds.follow("table", "limit=10")["data"]
        assert data[array.body["id"]] == [
            [1, 2],
            [2, 3],
            [3, 1],
            [1, 2],
            [2, 3],
            [3, 1],
            [1, 2],
            [2, 3],
            [3, 1],
            [1, 2]
        ]

        ds.delete()
