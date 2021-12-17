// @ts-ignore
import yarrrml from "@rmlio/yarrrml-parser/lib/rml-generator";
import express from "express";

const app = express();
const port = 3000;

// take yarrrml as input and return triples
app.get('/', (req, res) => {
    const y2r = new yarrrml();
    const yarrrml_query = req.query.yarrrml;
    if (yarrrml_query) {
        const triples: string = y2r.convert(yarrrml_query);
        if ( y2r.getLogger().has('error') ) {
            return res.status(400).send(y2r.getLogger().getAll());
        }
        return res.send(triples);
    }
    return res.status(422).send();
})

app.listen(port, () => {
    return console.log(`server is listening on ${port}`);
});