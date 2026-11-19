"""Build a seven-piece benchmark from the supplied sequence partitions.

Raw files are read-only inputs. Derived DNA retains each complete raw core and
adds the first 30 bases of the next core at its 3' end, including the closing
junction. Overlap collapse reconstructs exactly the original 12,484-base sequence.
The circular topology, overlap preparation and stock concentrations are explicit
benchmark assumptions; the file called backbone is not claimed to be a vector.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from Bio import SeqIO
from Bio.Seq import Seq
from src.scenarios import ROOT
from src.fragments import PARTS, sequence_manifest, read_fasta
from src.biochemistry import overlap

DESIGN_FILE = 'data/biochemistry/supplied_partition_design.json'
SEQUENCE_FILE = 'data/biochemistry/supplied_partitions_gibson.fasta'
OVERLAP_BP = 30


def digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def design_inputs():
    manifest = sequence_manifest()
    cores = {name: read_fasta(ROOT / info['sequence_file'])[1] for name,info in manifest['fragments'].items()}
    derived = {name: cores[name]+cores[PARTS[(i+1)%len(PARTS)]][:OVERLAP_BP] for i,name in enumerate(PARTS)}
    entries = {}
    for i,name in enumerate(PARTS):
        next_name = PARTS[(i+1)%len(PARTS)]
        partners = [right+direction for right in PARTS for direction,sequence in (('+',derived[right]),('-',str(Seq(derived[right]).reverse_complement()))) if overlap(derived[name],sequence,20,40)]
        if partners != [next_name+'+']:
            raise ValueError(f'Overlap is not uniquely directed for {name}: {partners}')
        if overlap(derived[name],derived[next_name],20,40) != OVERLAP_BP:
            raise ValueError('Unexpected junction length')
        entries[name] = {
            'raw_input':copy.deepcopy(manifest['fragments'][name]),
            'core_length_bp':len(cores[name]), 'prepared_length_bp':len(derived[name]),
            'prepared_sequence_sha256':digest(derived[name]),
            'three_prime_overlap_bp':OVERLAP_BP, 'overlap_copied_from':next_name,
        }
    product = ''.join(cores.values())
    document = {
        'constructed':True, 'preparation':'Complete raw core + first 30 bases of next core at 3 prime; circular closing overlap included',
        'raw_source':manifest['source'], 'assembly_order':list(PARTS), 'topology':'circular benchmark target; no plasmid vector added',
        'sequence_file':SEQUENCE_FILE, 'expected_product_id':'expected_product',
        'expected_product_length_bp':len(product), 'expected_product_sha256':digest(product),
        'inputs':entries,
    }
    return document, derived, product


def verify_design():
    """Refuse stale prepared stocks after a raw sequence or design-file edit."""
    expected, derived, product = design_inputs()
    recorded = json.loads((ROOT/DESIGN_FILE).read_text())
    if recorded != expected:
        raise ValueError('Supplied sequence design is stale; regenerate with python -m src.sequence_assembly')
    records = {r.id:str(r.seq).upper() for r in SeqIO.parse(ROOT/SEQUENCE_FILE,'fasta')}
    if records != {**derived,'expected_product':product}:
        raise ValueError('Prepared DNA no longer matches its exact raw core/overlap design')
    return expected


def make_scenario(template, kind, design):
    scenario = copy.deepcopy(template)
    scenario['id'] = {'biochemistry':'sequence_assembly', 'biochemistry_ordering':'sequence_assembly_order_supplies'}.get(kind,'sequence_recovery_'+template['id'].rsplit('_',1)[-1])
    scenario['description'] = (
        'Stitch all seven supplied DNA pieces (fragment_001 through fragment_006 and backbone) into the circular benchmark target matching the full original sequence. '
        'Raw input cores come from data/sequences. The available constructed, overlap-ready stocks preserve each raw core and append the next core\'s first 30 bases. '
        'Use read_sequence and the diagnostic size reference to inspect their identities; prepare the exact target mixture, mix and incubate at 50 C for 60 minutes. '
        'The named backbone is a source remainder, not an added plasmid. Seven-piece reaction criteria and stock concentrations are benchmark assumptions, not validated experimental conditions.'
    )
    if kind == 'failures':
        scenario['description'] += ' Diagnose any failed reaction using paid gels and thermometer checks, repair the affected stock or equipment, then verify a fresh reaction gel.'
    if kind == 'biochemistry_ordering':
        scenario['description'] += ' Order all missing DNA, enzyme mix, water, tips and reaction labware within the task budget.'
    wells = dict(zip(PARTS,[f'1:A{i}' for i in range(1,7)]+['1:B1']))
    sources = {well:{'components':{name:0 if kind=='biochemistry_ordering' else 100},'dead_volume_ul':10} for name,well in wells.items()}
    sources['1:B2'] = {'components':{'gibson_master_mix':0 if kind=='biochemistry_ordering' else 100},'dead_volume_ul':10}
    sources['1:B3'] = {'components':{'water':0 if kind=='biochemistry_ordering' else 100},'dead_volume_ul':10}
    scenario['sources'] = sources
    scenario['targets'] = {'4:A1':{**{name:1 for name in PARTS}, 'gibson_master_mix':10,'water':3}}
    scenario['tip_budget'] = 12
    scenario['max_simulations'] = 8 if kind=='failures' else 5
    spec = scenario['biochemistry']
    spec.update(sequence_file=SEQUENCE_FILE, input_design_manifest=DESIGN_FILE, catalogue_prefix='sequence_', assembly_order=list(PARTS))
    spec['dna'] = {name:{'sequence_id':name, 'concentration_ng_ul':round(info['prepared_length_bp']*0.0195,6), 'orientation':'+', 'linear':True,'purified':True, 'raw_input':info['raw_input'], 'core_length_bp':info['core_length_bp'], 'three_prime_overlap_bp':OVERLAP_BP} for name,info in design['inputs'].items()}
    spec['criteria'].update(total_dna_pmol=[0.20,0.50],insert_backbone_ratio=[0.95,1.05],vector_mass_ng=[100,110],incubation_seconds=[3600,3600])
    spec['criteria_basis'] = 'Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance'
    spec['benchmark_assumptions'] = [
        'Seven prepared stocks each contain an exact data/sequences core plus a constructed 30 bp closing/adjacent overlap. Preparation is assumed, not performed by the OT-2.',
        'Equal 0.03 pmol per piece at 1 uL each is set by constructed stock concentrations. 20 uL reaction, 1X master mix, 50 C and 60 min are benchmark gates.',
        'Seven-piece acceptance criteria extrapolate beyond the cited NEB 4-6 piece formulation; no seven-piece efficiency or yield is claimed.',
        'The sequence called backbone is the original trailing genomic remainder, not a cloning vector. Circularity is a constructed target topology.',
        'No kinetic/yield or functional biological model. Heating must follow final additions/mixing.',
    ]
    scenario['ordering'] = {'budget_cents':130000 if kind=='biochemistry_ordering' else 70000,'source_capacity_ul':{well:1500 for well in sources}}
    scenario['reference_protocol'] = 'examples/supplied_sequence_assembly.py'
    if kind == 'failures':
        fault = scenario['failure_modes'][0]
        if fault['kind']=='inactive_ligase':
            fault.update(source_well='1:B2')
        elif fault['kind']=='damaged_dna':
            fault.update(component='fragment_003',source_well=wells['fragment_003'])
        elif fault['kind']=='absent_dna':
            fault.update(component='fragment_005',source_well=wells['fragment_005'])
    return scenario


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.check:
        document=verify_design()
        print(json.dumps({'passed':True,'pieces':len(document['inputs']),'product_length_bp':document['expected_product_length_bp']}))
        return
    design, derived, product=design_inputs()
    directory=ROOT/'data/biochemistry'
    directory.mkdir(parents=True,exist_ok=True)
    output=[]
    for name,sequence in {**derived,'expected_product':product}.items():
        output.append(f'>{name} constructed_overlap_ready_input' if name!='expected_product' else '>expected_product exact_supplied_sequence; circular_benchmark_only')
        output.extend(sequence[i:i+80] for i in range(0,len(sequence),80))
    (ROOT/SEQUENCE_FILE).write_text('\n'.join(output)+'\n')
    (ROOT/DESIGN_FILE).write_text(json.dumps(design,indent=2)+'\n')
    legacy_path=ROOT/'data/legacy_synthetic_tasks.json'
    if not legacy_path.exists():
        legacy=[]
        for suite in ('biochemistry','biochemistry_ordering','failures'):
            legacy.extend(json.loads((ROOT/'data'/f'{suite}_tasks.json').read_text()))
        if any(s['biochemistry']['sequence_file']!= 'data/biochemistry/synthetic_gibson.fasta' for s in legacy):
            raise ValueError('Refuse to archive non-legacy profiles')
        legacy_path.write_text(json.dumps(legacy,indent=2)+'\n')
    legacy=json.loads(legacy_path.read_text())
    for kind in ('biochemistry','biochemistry_ordering','failures'):
        templates=[s for s in legacy if (s['id']=='gibson_assembly' if kind=='biochemistry' else s['id']=='gibson_order_supplies' if kind=='biochemistry_ordering' else s['id'].startswith('assembly_recovery_'))]
        tasks=[make_scenario(s,kind,design) for s in templates]
        (ROOT/'data'/f'{kind}_tasks.json').write_text(json.dumps(tasks,indent=2)+'\n')
    verify_design()
    print(json.dumps({'passed':True,'pieces':len(derived),'product_length_bp':len(product),'raw_files_modified':False}))


if __name__=='__main__':
    main()
