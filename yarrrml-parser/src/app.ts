// @ts-ignore
import Yarrrml from "@rmlio/yarrrml-parser/lib/rml-generator";
import express from "express";
import bodyParser from "body-parser"

const app = express();
const port = 3000;

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

// take yarrrml as input and return triples
app.post('/', (req, res) => {
    const y2r = new Yarrrml();
    const yarrrml_query = req.body.yarrrml;
    if (yarrrml_query) {
        const quads = y2r.convert(yarrrml_query);
        const triples: string[] = [];
        quads.forEach((q: { subject: { value: string; }; predicate: { value: string; }; object: { termType: string; value: string; }; }) => {
            triples.push(`<${q.subject.value}> <${q.predicate.value}> ${q.object.termType === 'Literal' ? `"${q.object.value}"` : `<${q.object.value}>`} .`);
        });
        if (y2r.getLogger().has('error')) {
            return res.status(400).send(y2r.getLogger().getAll());
        }
        return res.send(triples.join('\r\n'));
    }
    return res.status(422).send();
})

app.listen(port, () => {
    return console.log(`server is listening on ${port}`);
});