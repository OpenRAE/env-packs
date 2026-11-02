// Package document decodes the pack-owned YAML and JSON documents strictly and
// within the validation limits (design 0005). RAES-owned documents use the
// RAES loaders instead.
//
// Each failure is an [*Error] with a stable [Code]. An error never holds the
// text of the document or of the parser.
package document
