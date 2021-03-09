import requests

import pandas as pd

from string import Template

from tqdm import tqdm

tqdm.pandas()


def get_data_from_vivino(term):
    VIVINO_INDEX_URL = (
        "https://9takgwjuxl-dsn.algolia.net/1/indexes/WINES_prod/query?x-algolia-agent=Algolia%20for%20JavaScript%20(3.33.0)"
        "%3B%20Browser%20(lite)&x-algolia-application-id=9TAKGWJUXL&x-algolia-api-key=60c11b2f1068885161d95ca068d3a6ae"
    )

    r = requests.post(VIVINO_INDEX_URL, json={"params": f"query={term}&hitsPerPage=6"})
    r.raise_for_status()
    data = r.json()

    hit = data["hits"][0]

    return pd.Series(
        {
            "url": "https://www.vivino.com/{seo_name}/w/{id}".format(**hit),
            "ratings_average": hit["statistics"]["ratings_average"],
            "ratings_count": hit["statistics"]["ratings_count"],
        }
    )


def main():
    bebidas = requests.get("https://app.cbgbdistribucion.com.ar/api/v1/bebidas/").json()

    bebidas_df = pd.DataFrame.from_records(
        bebidas,
        columns=["categoria", "marca", "descripcion", "variedad", "precio_unidad"],
    )

    vinos = bebidas_df.loc[bebidas_df["categoria"] == "VINOS"]

    search_strings = vinos[["categoria", "descripcion", "variedad"]].apply(
        lambda row: " ".join(row.values), axis=1
    )

    vivino_data = search_strings.progress_apply(get_data_from_vivino)

    full_data = pd.concat([vinos, vivino_data], axis=1)

    html_table = full_data.to_html(
        table_id="vinos",
        columns=[
            "marca",
            "descripcion",
            "variedad",
            "precio_unidad",
            "ratings_average",
            "ratings_count",
            "url",
        ],
    )

    TEMPLATE = Template(
        """<html>
    <head>
        <title>CBGB explorer</title>
    </head>



    <script src="https://code.jquery.com/jquery-3.5.1.js" type="text/javascript"></script>
    <script src="https://cdn.datatables.net/1.10.23/js/jquery.dataTables.min.js" type="text/javascript"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.10.23/css/jquery.dataTables.min.css" />

    <script>
        /* Custom filtering function which will search data in column four between two values */
    $.fn.dataTable.ext.search.push(
        function( settings, data, dataIndex ) {
            var min = parseInt( $('#min').val(), 10 );
            var max = parseInt( $('#max').val(), 10 );
            var price = parseFloat( data[4] ) || 0; // use data for the price column

            if ( ( isNaN( min ) && isNaN( max ) ) ||
                ( isNaN( min ) && price <= max ) ||
                ( min <= price   && isNaN( max ) ) ||
                ( min <= price   && price <= max ) )
            {
                return true;
            }
            return false;
        }
    );

    $(document).ready(function() {
        var table = $('#vinos').DataTable();

        // Event listener to the two range filtering inputs to redraw on input
        $('#min, #max').keyup( function() {
            table.draw();
        } );
    } );
    </script>

    <body>
       <table border="0" cellspacing="5" cellpadding="5">
            <tbody><tr>
                <td>Precio minimo:</td>
                <td><input type="text" id="min" name="min"></td>
            </tr>
            <tr>
                <td>Precio maximo:</td>
                <td><input type="text" id="max" name="max"></td>
            </tr>
        </tbody></table>

        $table

    </body>
    </html>
    """
    )

    with open("vinos.html", "w") as fh:
        fh.write(TEMPLATE.safe_substitute({"table": html_table}))


if __name__ == "__main__":
    main()
