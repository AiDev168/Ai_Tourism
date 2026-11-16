"""Executable no-network tests for Rahgard's read-only ZIP preflight."""
import csv
import io
import unittest
import zipfile

from scripts.rahgard_archive_preflight import UnsafeArchive, inspect


def zipped(files: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return out.getvalue()


def csv_payload(rows: list[tuple[str, str]]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["destination_key", "canonical_name"])
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


class ArchivePreflightTests(unittest.TestCase):
    def test_nested_duplicate_delivery_does_not_claim_unique_places(self):
        csv_data = csv_payload([("a", "باغ"), ("b", "مسجد")])
        inner_a = zipped({"batch-a/destinations.csv": csv_data})
        inner_b = zipped({"batch-b/destinations.csv": csv_data})
        result = inspect(zipped({"one.zip": inner_a, "two.zip": inner_b}))
        self.assertEqual(result["csv_file_count"], 2)
        self.assertEqual(result["distinct_csv_content_count"], 1)
        self.assertEqual(len(result["duplicate_csv_content_groups"]), 1)
        self.assertEqual(result["csv_row_total_including_duplicate_deliveries"], 4)
        self.assertIs(result["publication_approved"], False)
        self.assertIs(result["database_modified"], False)

    def test_preserves_persian_headers_and_rows(self):
        content = csv_payload([("a", "مسجد امام"), ("a", "مسجد امام")])
        report = inspect(zipped({"a.csv": content}))
        self.assertEqual(report["csv"][0]["row_count"], 2)
        self.assertEqual(report["csv"][0]["unique_destination_keys"], 1)
        self.assertEqual(report["csv"][0]["repeated_destination_keys_in_file"], 1)

    def test_rejects_parent_traversal(self):
        with self.assertRaises(UnsafeArchive):
            inspect(zipped({"../evil.csv": b"key\n1\n"}))

    def test_rejects_oversized_member(self):
        from unittest.mock import patch
        with patch("scripts.rahgard_archive_preflight.MAX_MEMBER_BYTES", 3):
            with self.assertRaises(UnsafeArchive):
                inspect(zipped({"file.csv": b"ab,cd\n"}))

    def test_rejects_malformed_csv(self):
        with self.assertRaises(UnsafeArchive):
            inspect(zipped({"data.csv": b"destination_key,name\na,b,c\n"}))

    def test_rejects_short_csv_rows_and_duplicate_headers(self):
        for body in (b"a,b\n1\n", b"a,a\n1,2\n"):
            with self.subTest(body=body), self.assertRaises(UnsafeArchive):
                inspect(zipped({"data.csv": body}))

    def test_duplicate_member_names_are_rejected(self):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("same.csv", b"destination_key,name\na,A\n")
            archive.writestr("same.csv", b"destination_key,name\nb,B\n")
        with self.assertRaises(UnsafeArchive):
            inspect(out.getvalue())

    def test_external_record_ids_are_not_mislabeled_destination_keys(self):
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["external_id", "name"])
        writer.writerow(["source-1", "A"])
        writer.writerow(["source-2", "B"])
        report = inspect(zipped({"data.csv": out.getvalue().encode("utf-8")}))
        row = report["csv"][0]
        self.assertEqual(row["identity_key_field"], "external_id")
        self.assertEqual(row["unique_identity_keys"], 2)
        self.assertNotIn("unique_destination_keys", row)

    def test_rejects_non_archive(self):
        with self.assertRaises(UnsafeArchive):
            inspect(b"not a ZIP")


if __name__ == "__main__":
    unittest.main()
