from ingest.base import BaseExtractor, File

# ZIP history is RDC_Inventory_Core_Metrics_Zip_History.csv, 837 MB; the only model using this source is metro-level
URL = "https://econdata.s3-us-west-2.amazonaws.com/Reports/Core/RDC_Inventory_Core_Metrics_Metro_History.csv"


class Realtor(BaseExtractor):
    """Realtor.com research inventory by metro, monthly since July 2016."""

    source = "realtor"

    def files(self):
        return [
            File(
                "metro_inventory",
                URL,
                "RDC_Inventory_Core_Metrics_Metro_History.csv",
                refresh=True,
            )
        ]
