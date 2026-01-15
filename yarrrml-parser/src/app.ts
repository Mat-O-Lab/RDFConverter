// @ts-ignore
import Yarrrml from "@rmlio/yarrrml-parser/lib/rml-generator";
import express from "express";
import bodyParser from "body-parser";
import * as yaml from "js-yaml";

const app = express();
const port = process.env.PORT;

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

// take yarrrml as input and return triples
app.post('/', (req, res) => {
    console.log(req.body.yarrrml)
    const y2r = new Yarrrml();
    const yarrrml_query = req.body.yarrrml;
    if (yarrrml_query) {
        // Extract base IRI from YARRRML document
        let baseIRI = 'http://example.com/'; // default fallback
        try {
            const parsed = yaml.load(yarrrml_query);
            if (parsed && typeof parsed === 'object' && 'base' in parsed) {
                baseIRI = (parsed as any).base;
                console.log('✓ Using base IRI from YARRRML:', baseIRI);
            } else {
                console.log('ℹ No base IRI found in YARRRML, using default:', baseIRI);
            }
        } catch (e) {
            console.warn('⚠ Could not parse YARRRML to extract base, using default:', baseIRI);
        }
        
        // Pass baseIRI as option to convert method
        const quads = y2r.convert(yarrrml_query, { baseIRI: baseIRI });
        console.log(quads)
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
