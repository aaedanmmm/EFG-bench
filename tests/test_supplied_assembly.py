"""Seven-piece raw-sequence provenance and real-SDK assembly/recovery checks."""
import asyncio
import copy
import json
import hashlib
import shutil
from types import SimpleNamespace
import pytest
from Bio import SeqIO
from inspect_ai.scorer import CORRECT, Target
from inspect_ai.util import Store
from src import environment, fragments, sequence_assembly
from src.biochemistry import circular_equal, evaluate_biochemistry
from src.costs import get_catalogue
from src.failures import diagnostic_reference, gel_assay, human_service, fingerprint
from src.fragments import PARTS, sequence_manifest
from src.ordering import OrderError, new_account, place_order
from src.runner import validate_code
from src.scenarios import ROOT, get_scenario, load_scenarios
from src.scorer import ot2_mixture

REFERENCE=(ROOT/'examples/supplied_sequence_assembly.py').read_text()


def check(scenario, code=REFERENCE):
    return asyncio.run(validate_code(code,scenario['id'],inventory=scenario))


def test_all_active_assembly_suites_use_all_seven_real_cores():
    design=sequence_assembly.verify_design()
    raw=sequence_manifest()
    for suite in ('biochemistry','biochemistry_ordering','failures'):
        for scenario in load_scenarios(suite):
            assert set(scenario['biochemistry']['dna']) == set(PARTS)
            assert scenario['biochemistry']['sequence_file'] == sequence_assembly.SEQUENCE_FILE
            assert scenario['biochemistry']['assembly_order'] == list(PARTS)
            for name,entry in scenario['sequence_inventory'].items():
                assert entry['raw_input'] == raw['fragments'][name]
                core=fragments.read_sequence_metadata(entry['raw_input'])
                stock=fragments.read_sequence_metadata(entry)
                assert stock[:len(core)] == core
                assert len(stock)==len(core)+30
                assert entry['sha256']==design['inputs'][name]['prepared_sequence_sha256']


def test_all_seven_exact_unique_junctions_reconstruct_original():
    scenario=get_scenario('sequence_assembly')
    from src.biochemistry import load_assembly_inputs,check_junctions,new_report,assemble_circular_product
    assembly=load_assembly_inputs(scenario,scenario['biochemistry'])
    report=new_report(True)
    junctions=check_junctions(report,assembly,[20,40])
    assert len(junctions)==7
    assert all(c['passed'] for c in report['checks'])
    assert all(j['overlap_bp']==30 for j in junctions)
    original=str(SeqIO.read(ROOT/'data/sequences/ENST00000297261.7.fasta','fasta').seq)
    assert assemble_circular_product(assembly,junctions)==original
    assert assembly.expected_product==original
    assert len(original)==12484


def test_stale_prepared_sequence_rejected(tmp_path,monkeypatch):
    shutil.copytree(ROOT/'data',tmp_path/'data')
    monkeypatch.setattr(sequence_assembly,'ROOT',tmp_path)
    monkeypatch.setattr(fragments,'ROOT',tmp_path)
    path=tmp_path/sequence_assembly.SEQUENCE_FILE
    text=path.read_text(); head,rest=text.split('\n',1)
    rest=('A' if rest[0]!='A' else 'C')+rest[1:]
    path.write_text(head+'\n'+rest)
    with pytest.raises(ValueError,match='Prepared DNA no longer matches'):
        sequence_assembly.verify_design()


def test_stale_raw_input_rejected(tmp_path,monkeypatch):
    shutil.copytree(ROOT/'data',tmp_path/'data')
    monkeypatch.setattr(sequence_assembly,'ROOT',tmp_path)
    monkeypatch.setattr(fragments,'ROOT',tmp_path)
    path=tmp_path/'data/sequences/fragment_001.fasta'
    text=path.read_text(); head,rest=text.split('\n',1)
    path.write_text(head+' edited\n'+rest)
    with pytest.raises(ValueError,match='design is stale'):
        sequence_assembly.verify_design()


@pytest.fixture(scope='module')
def baseline():
    result=check(get_scenario('sequence_assembly'))
    assert result['passed'],result['errors']
    return result


def test_real_protocol_passes_full_seven_piece_model(baseline):
    bio=baseline['biochemistry']
    assert len(bio['checks'])==37
    assert all(c['passed'] for c in bio['checks'])
    assert bio['assembly']['predicted_sequence']==bio['assembly']['expected_sequence']
    assert len(bio['assembly']['predicted_sequence'])==12484
    assert bio['reactions'][0]['total_dna_pmol']==pytest.approx(0.21)
    assert len(bio['reactions'][0]['insert_backbone_ratios'])==6
    assert set(bio['reactions'][0]['insert_backbone_ratios'].values())=={1.0}
    assert baseline['tips_used']==9
    assert 'seven-piece' in next(c['basis'] for c in bio['checks'] if c['id'].endswith('.incubation'))


def test_missing_piece_and_correct_size_wrong_sequence_cannot_pass(baseline,monkeypatch,tmp_path):
    evidence=copy.deepcopy(baseline)
    del evidence['final_wells']['4:A1']['fragment_004']
    scenario=get_scenario('sequence_assembly')
    assert not evaluate_biochemistry(scenario,evidence)['passed']
    # Same-length mutation in a core must fail sequence identity, not pass on size.
    records=list(SeqIO.parse(ROOT/sequence_assembly.SEQUENCE_FILE,'fasta'))
    from Bio.Seq import Seq
    for record in records:
        if record.id=='fragment_004':
            seq=str(record.seq);record.seq=Seq(seq[:100]+('A' if seq[100]!='A' else 'C')+seq[101:])
    SeqIO.write(records,tmp_path/'mutated.fasta','fasta')
    from src import biochemistry
    monkeypatch.setattr(biochemistry,'ROOT',tmp_path)
    scenario['biochemistry']['sequence_file']='mutated.fasta'
    result=evaluate_biochemistry(scenario,baseline)
    assert not result['passed']
    assert any(c['id']=='product.sequence_identity' and not c['passed'] for c in result['checks'])


def test_seven_piece_ordering_delivers_correct_prepared_identities_and_scores():
    scenario=get_scenario('sequence_assembly_order_supplies')
    original=copy.deepcopy(scenario)
    account=new_account(scenario)
    for well,source in scenario['sources'].items():
        component=next(iter(source['components']))
        item='gibson_master_mix' if component=='gibson_master_mix' else 'nuclease_free_water' if component=='water' else 'sequence_'+component
        scenario,account,_=place_order(scenario,account,item,well)
    for item,slot in [('filtered_tips_20ul','2'),('temperature_reaction_plate','4')]:
        scenario,account,_=place_order(scenario,account,item,slot)
    result=asyncio.run(ot2_mixture()(SimpleNamespace(metadata={'scenario':original},store=Store({'protocol':REFERENCE,'ordering_account':account})),Target('')))
    assert result.value==CORRECT,result.explanation
    assert result.metadata['ordering']['spent_cents']==126650
    assert len(result.metadata['sequence_inventory'])==7


def test_raw_partition_cannot_be_substituted_for_prepared_stock():
    scenario=get_scenario('sequence_assembly')
    with pytest.raises(OrderError,match='Sequence identity'):
        place_order(scenario,new_account(scenario),'fragment_001','1:A1',replace=True)
    with pytest.raises(OrderError,match='Sequence identity'):
        place_order(scenario,new_account(scenario),'backbone','1:B1',replace=True)


def test_agent_sequence_tool_and_gel_reference_show_prepared_and_raw_sizes(monkeypatch):
    scenario=get_scenario('sequence_recovery_02')
    state=Store({'scenario':scenario,'ordering_account':new_account(scenario)})
    monkeypatch.setattr(environment,'store',lambda:state)
    visible=json.loads(asyncio.run(environment.get_environment()()))
    reference=visible['diagnostic_reference']
    assert reference['expected_product_size_bp']==12484
    assert [s['expected_intact_band_bp'] for s in reference['dna_sources']]==[772,1566,1135,648,1923,1300,5350]
    assert [s['raw_core_length_bp'] for s in reference['dna_sources']]==[742,1536,1105,618,1893,1270,5320]
    assert all(s['added_overlap_bp']==30 for s in reference['dna_sources'])
    read=json.loads(asyncio.run(environment.read_sequence()('sequence_fragment_003')))
    assert len(read['sequence'])==1135
    assert read['metadata']['raw_input']['length_bp']==1105
    assert 'failure_modes' not in visible['scenario']
    lane=json.loads(asyncio.run(environment.request_human_service()(service='run_gel',sample='1:A3')))['result']['assay']
    assert lane['component']=='fragment_003' and lane['expected_size_bp']==1135
    assert 1135 not in lane['bands_bp'] and lane['smear_range_bp']


@pytest.mark.parametrize('index',range(1,6))
def test_all_five_faults_recover_with_seven_dna_inputs(index):
    scenario=get_scenario(f'sequence_recovery_{index:02d}')
    account=new_account(scenario)
    before=check(scenario)
    assert before['liquid_handling_passed'] and not before['passed']
    fault=scenario['failure_modes'][0]
    if fault['kind']=='temperature_offset':
        scenario,account,receipt=human_service(scenario,account,'thermometer_check')
        assert receipt['result']['measured_temperature_c']==(62 if index==4 else 38)
        scenario,account,_=human_service(scenario,account,'calibrate_temperature')
    else:
        if index in (2,3):
            lane=gel_assay(scenario,fault['source_well'],'source')
            assert lane['expected_size_bp']==scenario['sequence_inventory'][fault['component']]['length_bp']
            assert not lane['bands_bp'] if index==3 else lane['smear_range_bp']
        item='gibson_master_mix' if fault['component']=='gibson_master_mix' else 'sequence_'+fault['component']
        scenario,account,_=place_order(scenario,account,item,fault['source_well'],replace=True)
    after=check(scenario)
    assert after['passed'],after['errors']
    reference=diagnostic_reference(scenario)
    assert reference['expected_product_size_bp']==12484
