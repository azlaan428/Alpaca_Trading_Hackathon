use crate::pipeline::TradeDecision;
use anyhow::Result;
use arrow2::array::{Float64Array, Utf8Array};
use arrow2::chunk::Chunk;
use arrow2::datatypes::{DataType, Field, Schema};
use arrow2::io::parquet::write::{
    CompressionOptions, Encoding, FileWriter, RowGroupIterator, Version, WriteOptions,
};
use std::fs::File;

pub fn write_parquet(records: &[TradeDecision], out_path: &str) -> Result<()> {
    let symbol: Utf8Array<i32> = records.iter().map(|r| Some(r.symbol.clone())).collect();
    let drop_pct: Float64Array = records.iter().map(|r| Some(r.drop_pct)).collect();
    let action: Utf8Array<i32> = records.iter().map(|r| Some(r.action.clone())).collect();
    let order_id: Utf8Array<i32> = records.iter().map(|r| r.order_id.clone()).collect();
    let price_at_decision: Float64Array =
        records.iter().map(|r| Some(r.price_at_decision)).collect();
    let timestamp: Utf8Array<i32> = records.iter().map(|r| Some(r.timestamp.clone())).collect();

    let schema = Schema::from(vec![
        Field::new("symbol", DataType::Utf8, false),
        Field::new("drop_pct", DataType::Float64, false),
        Field::new("action", DataType::Utf8, false),
        Field::new("order_id", DataType::Utf8, true),
        Field::new("price_at_decision", DataType::Float64, false),
        Field::new("timestamp", DataType::Utf8, false),
    ]);

    let chunk = Chunk::new(vec![
        symbol.boxed(),
        drop_pct.boxed(),
        action.boxed(),
        order_id.boxed(),
        price_at_decision.boxed(),
        timestamp.boxed(),
    ]);

    let options = WriteOptions {
        write_statistics: true,
        compression: CompressionOptions::Snappy,
        version: Version::V2,
        data_pagesize_limit: None,
    };

    let encodings: Vec<Vec<Encoding>> = schema
        .fields
        .iter()
        .map(|_| vec![Encoding::Plain])
        .collect();

    let row_groups = RowGroupIterator::try_new(
        vec![Ok(chunk)].into_iter(),
        &schema,
        options,
        encodings,
    )?;

    let file = File::create(out_path)?;
    let mut writer = FileWriter::try_new(file, schema, options)?;

    for group in row_groups {
        writer.write(group?)?;
    }
    writer.end(None)?;

    Ok(())
}