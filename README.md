# Download URLs for Annotation, Experiment, and File object tables 

- https://www.encodeproject.org/report.tsv?type=Annotation&annotation_type=ChromBPNet-model&annotation_type=ChromBPNet-bias-model&annotation_type=BPNet-control&annotation_type=BPNet-model&field=%40id&field=accession&field=targets.%40id&field=targets.label&field=biosample_ontology.term_name&field=description&field=lab.title&field=award.project&field=status&field=organism.scientific_name&field=relevant_life_stage&field=relevant_timepoint&field=relevant_timepoint_units&field=software_used.software.name&field=treatments.treatment_term_name&field=schema_version&field=related_files&field=alternate_accessions&field=analyses&field=dbxrefs&field=date_released&field=doi&field=internal_tags&field=biosample_ontology&field=documents&field=notes&field=date_created&field=submitted_by&field=references&field=award&field=aliases&field=uuid&field=annotation_type&field=annotation_subtype&field=assay_term_name&field=encyclopedia_version&field=trait&field=supersedes&field=experimental_input&field=donor&field=disease_term_id&field=treatments&field=post_treatment_time&field=post_treatment_time_units&field=%40type&field=original_files&field=contributing_files&field=files&field=revoked_files&field=assembly&field=hub&field=default_analysis&field=superseded_by&field=biochemical_inputs&field=disease_term_name
- https://www.encodeproject.org/report.tsv?type=Experiment&field=%40id&field=accession&field=assay_term_name&field=assay_title&field=biosample_ontology.classification&field=target.%40id&field=target.label&field=target.genes.symbol&field=biosample_summary&field=biosample_ontology.term_name&field=dbxrefs&field=description&field=lab.title&field=award.project&field=status&field=files.%40id&field=related_series&field=replicates.library.biosample.accession&field=replicates.biological_replicate_number&field=replicates.technical_replicate_number&field=replicates.antibody.accession&field=replicates.library.biosample.organism.scientific_name&field=replicates.library.biosample.life_stage&field=replicates.library.biosample.age_display&field=replicates.library.biosample.treatments.treatment_term_name&field=replicates.library.biosample.treatments.treatment_term_id&field=replicates.library.biosample.treatments.amount&field=replicates.library.biosample.treatments.amount_units&field=replicates.library.biosample.treatments.duration&field=replicates.library.biosample.treatments.duration_units&field=replicates.library.biosample.synchronization&field=replicates.library.biosample.post_synchronization_time&field=replicates.library.biosample.post_synchronization_time_units&field=replicates.library.biosample.applied_modifications.modified_site_by_target_id.organism&field=replicates.library.biosample.applied_modifications.introduced_gene.organism&field=replicates.%40id&field=replicates.library.mixed_biosamples&field=replicates.library.biosample.subcellular_fraction_term_name&field=replicates.library.construction_platform.term_name&field=replicates.library.construction_method&field=submitter_comment&field=biosample_ontology&field=documents&field=references&field=schema_version&field=alternate_accessions&field=analyses&field=date_released&field=doi&field=internal_tags&field=notes&field=date_created&field=submitted_by&field=award&field=aliases&field=uuid&field=date_submitted&field=possible_controls&field=supersedes&field=related_files&field=internal_status&field=pipeline_error_detail&field=control_type&field=bio_replicate_count&field=tech_replicate_count&field=replication_type&field=objective_slims&field=type_slims&field=category_slims&field=assay_slims&field=simple_biosample_summary&field=assay_term_id&field=assay_synonyms&field=%40type&field=original_files&field=contributing_files&field=revoked_files&field=assembly&field=hub&field=default_analysis&field=superseded_by&field=related_annotations&field=protein_tags&field=life_stage_age&field=perturbed
- https://www.encodeproject.org/report.tsv?type=File&field=%40id&field=title&field=accession&field=dataset&field=assembly&field=technical_replicates&field=biological_replicates&field=file_format&field=file_type&field=file_format_type&field=file_size&field=assay_term_name&field=biosample_ontology.term_name&field=biosample_ontology.organ_slims&field=simple_biosample_summary&field=origin_batches&field=target.label&field=href&field=derived_from&field=genome_annotation&field=replicate.library.accession&field=paired_end&field=paired_with&field=preferred_default&field=run_type&field=read_length&field=mapped_read_length&field=cropped_read_length&field=cropped_read_length_tolerance&field=mapped_run_type&field=read_length_units&field=output_category&field=output_type&field=index_of&field=quality_metrics&field=lab.title&field=award.project&field=step_run&field=date_created&field=analysis_step_version&field=restricted&field=submitter_comment&field=status&field=annotation_type&field=annotation_subtype&field=biochemical_inputs&field=encyclopedia_version&field=uuid&field=aliases&field=schema_version&field=award&field=submitted_by&field=notes&field=alternate_accessions&field=external_accession&field=read_count&field=file_format_specifications&field=no_file_available&field=submitted_file_name&field=md5sum&field=content_md5sum&field=fastq_signature&field=platform&field=read_name_details&field=flowcell_details&field=controlled_by&field=supersedes&field=replicate&field=dbxrefs&field=restriction_enzymes&field=content_error_detail&field=revoke_detail&field=read_structure&field=matching_md5sum&field=hotspots_prefix&field=filter_type&field=filter_value&field=pseudo_haplotype&field=%40type&field=upload_credentials&field=biological_replicates_formatted&field=donors&field=superseded_by&field=cloud_metadata&field=s3_uri&field=azure_uri&field=assay_title&field=biosample_ontology&field=target&field=targets&field=analyses&field=processed

# Cleaning Commands
```bash
cd resources/
qsv fmt Files.tsv --delimiter '\t' --out-delimiter '\t' > Files_Clean.tsv
qsv sqlp Annotations.tsv 'SELECT * from Annotations' --format parquet --output Annotations.parquet --delimiter '\t'
qsv sqlp Experiments.tsv 'SELECT * from Experiments' --format parquet --output Experiments.parquet --delimiter '\t'
qsv sqlp Files_Clean.tsv 'SELECT * from Files_Clean' --format parquet --output Files.parquet --delimiter '\t' --infer-len 0

cp ./output/BPNet-model.manifest /data/zusers/ramirezc/all_bpnet_files/
cp ./output/ChromBPNet-model.manifest /data/zusers/ramirezc/all_chrombpnet_files/
```

# Output fields

```ChromBPNet-model.tsv
Annotation accession
Annotation status
Annotation type
Genome assembly
Experiment accession
Experiment status
Description
Biosample summary
Biosample term name
Biosample classification
Assay name
Perturbed
training and test regions
observed signal profile
models
alignments
unfiltered alignments
selected regions for predicted signal and sequence contribution scores
predicted signal profile
bias-corrected predicted signal profile
profile sequence contribution scores
counts sequence contribution scores
bias models
sequence motifs
sequence motifs instances
normalized observed signal profile
normalized predicted signal profile
normalized bias-corrected predicted signal profile
sequence motifs report
```

```BPNet-model.tsv
Annotation accession
Annotation status
Annotation type
Genome assembly
Experiment accession
Experiment status
Description
Biosample summary
Biosample term name
Biosample classification
Assay name
Perturbed
observed signal profile (minus strand)
training and test regions
observed signal profile (plus strand)
models
selected regions for predicted signal and sequence contribution scores
profile sequence contribution scores
counts sequence contribution scores
predicted signal profile
normalized observed signal profile (plus strand)
normalized observed signal profile (minus strand)
observed control profile (plus strand)
observed control profile (minus strand)
alignments
unfiltered alignments
sequence motifs
sequence motifs instances
sequence motifs report
predicted signal profile (plus strand)
predicted signal profile (minus strand)
normalized predicted signal profile (plus strand)
normalized predicted signal profile (minus strand)
bidirectional peaks
unidirectional peaks
```
