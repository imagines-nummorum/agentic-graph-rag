import re

def generate_prefix(key):
    """Erzeugt CoEn aus composition_entity_id."""
    parts = key.split('_')
    prefix_parts = [p[:2].capitalize() for p in parts if p.lower() != 'id']
    return "".join(prefix_parts) if prefix_parts else "No"

def get_alias_label(key):
    parts = key.split('_')
    pascal = "".join(x.capitalize() for x in parts if x.lower() != 'id')
    return pascal if pascal else "Node"

def reduce_unit_for_llm(input_text):
    # Vorbereitung
    lines = [line.replace('*', '').strip() for line in input_text.strip().split('\n') if line.strip()]
    
    node_registry = {}  
    alias_to_label = {} # Mappt CoEn auf das Label (z.B. CompositionEntity)
    auto_counters = {}  
    relations = []
    
    for line in lines:
        nodes_in_line = []
        stack, inside_string, start_idx = 0, False, -1
        
        # State-Machine für Node-Extraktion
        for i, char in enumerate(line):
            if char == '"' and (i == 0 or line[i-1] != '\\'):
                inside_string = not inside_string
            if not inside_string:
                if char == '(':
                    if stack == 0: start_idx = i
                    stack += 1
                elif char == ')':
                    stack -= 1
                    if stack == 0:
                        nodes_in_line.append((start_idx, i + 1, line[start_idx:i+1]))
        
        if len(nodes_in_line) < 2: continue

        line_aliases = []
        for start, end, node_str in nodes_in_line:
            content = node_str[1:-1]
            id_match = re.search(r'([\w_]+_id)["\s:]+([^",}]+)', content)
            
            if id_match:
                key, val = id_match.group(1), id_match.group(2).strip('"')
                label = get_alias_label(key)
                prefix = generate_prefix(key)
                
                # Mapping Alias-Typ -> Label für die Legende
                if prefix not in alias_to_label:
                    alias_to_label[prefix] = label
                
                if val not in node_registry:
                    if val.isdigit():
                        idx = val
                    else:
                        auto_counters[prefix] = auto_counters.get(prefix, 0) + 1
                        idx = auto_counters[prefix]
                    
                    alias = f"{prefix}{idx}"
                    # Keys unquoten für sauberes LLM-Input
                    node_decl = re.sub(r'^([\w:]+)', r'**\1**', content)
                    node_decl = re.sub(r'"(\w+)"\s*:', r'\1:', node_decl)
                    node_registry[val] = {'alias': alias, 'full_def': f"{alias} {node_decl}"}
                
                line_aliases.append(node_registry[val]['alias'])

        # Relation extrahieren
        first_node_end = nodes_in_line[0][1]
        second_node_start = nodes_in_line[1][0]
        rel_string = line[first_node_end:second_node_start].strip()
        rel_string = re.sub(r'\{\s*\}', '', rel_string)
        
        if len(line_aliases) >= 2:
            relations.append(f"({line_aliases[0]}){rel_string}({line_aliases[1]})")

    # --- OUTPUT ---
    output = []

    #output = ["## Aliases"]
    #for pref, label in sorted(alias_to_label.items()):
    #    output.append(f"* {pref} = {label}")
    
    output.append("\n### Nodes")
    for node in node_registry.values():
        output.append(f"* {node['full_def']}")
    
    output.append("\n### Relations")
    for rel in relations:
        output.append(f"* {rel}")

    # Finaler Sweep: Alle {} entfernen

    output = "\n".join(output).replace(' ]', ']')

    # Remove Fixtures
    output = re.sub(r'(^|:?)Fixture', '', output)
    # Remove _ids
    output = re.sub(r'[a-zA-Z_]+_id:[0-9,]+', '', output)
    # Remove path_ids
    output = re.sub(r'[a-zA-Z_]+path_ids:[0-9,\[\]]+', '', output)
    output = output.replace(',}', '}').replace('{,', '{')

    return output