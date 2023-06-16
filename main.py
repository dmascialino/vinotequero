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

    term = term.replace("&", "")
    r = requests.post(VIVINO_INDEX_URL, json={"params": f"query={term}&hitsPerPage=6"})
    r.raise_for_status()
    data = r.json()

    for hit in data["hits"]:
        winery = hit.get("winery")
        if winery is None:
            continue
        address = winery.get("address")
        if address:
            country = address.get("country")
            if country == "ar":
                break
        region = winery.get("region")
        if region:
            country = region.get("country")
            if country == "ar":
                break
    else:
        # nothing useful found :/
        return pd.Series(
            {}
        )

    return pd.Series(
        {
            "url": "https://www.vivino.com/{seo_name}/w/{id}".format(**hit),
            "ratings_average": hit["statistics"]["ratings_average"],
            "ratings_count": hit["statistics"]["ratings_count"],
        }
    )


def clean_price(s):
    return s.replace(".", "").replace("$", "").replace(",00", "")


def main():
    bebidas = requests.get("https://app.cbgbdistribucion.com.ar/api/v1/bebidas/").json()

    bebidas_df = pd.DataFrame.from_records(
        bebidas,
        columns=["categoria", "marca", "descripcion", "variedad", "precio_unidad"],
    )

    bebidas_df["sitio"] = "cbgb"

    vinos = bebidas_df.loc[bebidas_df["categoria"] == "VINOS"]
    vinos = vinos.loc[~bebidas_df["descripcion"].str.contains("LA EMPRESA PERMANECERÁ")]

    mp_tables = pd.read_html("https://mpdrinks.com.ar/lista-de-precios/", decimal=",", thousands=".",
            converters={'Precio Efectivo x Unidad': clean_price}, displayed_only=True)
    mp_vinos = mp_tables[2].rename(columns={"Unnamed: 0": "descripcion",
        "Precio Efectivo x Unidad": "precio_unidad"})[["descripcion", "precio_unidad"]]
    mp_vinos["sitio"] = "mp_drinks"

    vinos = pd.concat([vinos, mp_vinos])

    search_strings = vinos[["marca", "descripcion", "variedad"]].apply(
        lambda row: " ".join(row.dropna().values), axis=1
    )

    vivino_data = search_strings.progress_apply(get_data_from_vivino)

    full_data = pd.concat([vinos, vivino_data], axis=1)

    html_table = full_data.to_html(
        table_id="vinos",
        columns=[
            "sitio",
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
