// #include "new_org.h"

// #include <stdio.h>

typedef enum {
  D,
  W,
  REG,
  MOD,
  RM,
  DISP_LO,
  DISP_HI,
  ADDR_LO,
  ADDR_HI,
  DATA,
  DATA_IF_W,
} NamedFieldType;

typedef struct {
  NamedFieldType type;
  unsigned char bit_width;
} NamedField;

typedef struct {
  unsigned char bit_width;
  unsigned char literal_value;
} LiteralField;

typedef enum { NAMED_FIELD, LITERAL_FIELD } SchemaFieldType;

typedef struct {
  SchemaFieldType type;
  union {
    NamedField named;
    LiteralField literal;
  } field;
} SchemaField;

typedef struct {
  NamedField named_field;
  unsigned char parsed_value;
} ParsedNamedField;

typedef struct {
  char *mnemonic;
  LiteralField identifier_literal;
  SchemaField *instruction_schema;
  ParsedNamedField *implied_values;
} InstructionSchema;

int main(void) {}
