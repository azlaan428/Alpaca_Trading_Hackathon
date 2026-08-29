mod pipeline;
mod serialization;

use std::path::Path;

fn main() -> anyhow::Result<()> {
    let input_path = Path::new("../../memory_log.json");
    let output_path = "trade_decisions.parquet";

    println!("reading {}", input_path.display());
    let records = pipeline::load_and_validate(input_path)?;
    println!("loaded {} valid trade decisions", records.len());

    if records.is_empty() {
        println!("nothing to write, memory_log.json is empty or missing");
        return Ok(());
    }

    serialization::write_parquet(&records, output_path)?;
    println!("wrote {} rows to {}", records.len(), output_path);

    Ok(())
}