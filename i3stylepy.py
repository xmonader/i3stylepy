import sys
import os
import re
import argparse
from yaml import load, dump

t_windowcolors = "client.{state} {border} {background} {indicator}\n"
t_barcolors = "\t{state} {border} {background} {text}"

def get_window_colors(s):
    """
    Extracts window color attributes (focused|focused_inactive|unfocused|urgent) from i3 config s
    @param s str: config file content
    """
    d = {'window_colors':{}}
    pat = 'client\.(?P<property>focused|focused_inactive|unfocused|urgent)\s+(?P<colorstring>.+)'
    try:
        for m in re.finditer(pat, s):
            vals =  [val.strip() for val in m.groupdict()['colorstring'].split()]
            indicator = ''
            if len(vals) == 4:
                border, background, text, indicator = vals
            elif len(vals) == 3:
                border, background, text = vals
                indicator = ''
            prop = m.groupdict()['property']
            d['window_colors'][prop] = {}
            d['window_colors'][prop]['border'] = border
            d['window_colors'][prop]['text'] = text
            d['window_colors'][prop]['background'] = background
            d['window_colors'][prop]['indicator'] = indicator

    except: pass

    return d

def get_bar_colors(s):
    """
    Extracts bar/colors from config.

    @param s str: i3 config file contents.
    """
    d = {'bar_colors': {}}
    pat_colorbar = "\s*bar\s+{\s+.+?\s+colors\s+{\s+(?P<colorbar>.+)\s+}"
    m = None
    try:
        m = next(re.finditer(pat_colorbar, s, re.DOTALL))
    except: pass
    if m is not None:
        colorbar = m.groupdict()['colorbar']
        pat_color = "\s*(?P<property>\w+)\s+(?P<colorstring>.+)"


        for m in re.finditer(pat_color, colorbar, re.M):
            prop = m.groupdict()['property']
            attrs = [val.strip() for val in m.groupdict()['colorstring'].split()]
            d['bar_colors'][prop] = {}
            if len(attrs) == 3:
                d['bar_colors'][prop]['border'] = attrs[0]
                d['bar_colors'][prop]['background'] = attrs[1]
                d['bar_colors'][prop]['text'] = attrs[2]
            else: #1? defensive maybe
                d['bar_colors'][prop] = attrs[0]
    return d

def theme_from_config_string(config):
    """
    Collect theme info from config

    @param config str: i3 config contents
    """
    theme = {}
    theme['meta'] = 'Autogenerated theme'
    theme['window_colors']=get_window_colors(config)['window_colors']
    theme['bar_colors']=get_bar_colors(config)['bar_colors']
    return theme

def read_theme_from_yaml(ymlstring):
    """
    Load yaml theme into object

    @param ymlstring str: yaml dumped theme
    """
    return load(ymlstring)

def theme_as_yaml(themedict):
    """
    Dump theme object as yaml

    @para themedict dict: theme dict.
    """
    return dump(themedict, default_flow_style=False)

def apply_theme_to_config(themeyaml, configstring):
    """
    Apply theme (yaml) file to i3 configuration contents

    @param themeyaml str: theme serialized as yaml.
    @param configstring str: i3 configuration file contents.
    """
    theme = read_theme_from_yaml(themeyaml)
    themecolors = theme.get('colors', {})
    def solve_color(d, k):
        return themecolors.get(d[k], d[k])
    barcolors = get_bar_colors(configstring)['bar_colors'] #old ones.
    tbarcolors = theme['bar_colors']
    barcolors.update(tbarcolors)

    window_colors = get_window_colors(configstring)['window_colors'] # old ones.
    twincolors = theme['window_colors']
    window_colors.update(twincolors)

    #barcolors block string
    barcolors_props = ""
    for k, v in barcolors.items():
        if isinstance(v, dict):
            barcolors_props += "\n"+ t_barcolors.format(state=k, border=solve_color(v, 'border'), background=solve_color(v, 'background'), text=solve_color(v, 'text')) + "\n"
        elif isinstance(v, str):
            postedv=None
            if "#" in v:
                postedv = v
            else:
                if isinstance(themecolors, dict):
                    barcolors_props += "\n\t" + k + " " + themecolors.get(v, v)
    # print(barcolors_props)
    colorsblock = """
    colors {
    %s
    }
"""%(barcolors_props)
    mergedconfig = ""
    inbar = False

    configstring = re.sub("colors\s+{\s+(.+?)\s+}", "", configstring, flags=re.DOTALL)
    for line in configstring.splitlines():
        if "client." in line:
            continue #will be pushed later

        if line.strip().startswith("#"):
            mergedconfig += line + "\n"
            continue
        if "bar {" in line:
            inbar = True
            #mergedconfig += line +"\n"
        if inbar and "}" in line:
            mergedconfig += colorsblock
            inbar = False
        mergedconfig += line + "\n"
    #dump client. templates.
    for k, v in window_colors.items():
        mergedconfig += t_windowcolors.format(state=k, border=solve_color(v, 'border'), background=solve_color(v, 'background'), text=solve_color(v, 'text'), indicator=solve_color(v,'indicator'))

    return mergedconfig

def applytheme(themefile, configfile):
    """
    Apply theme file to i3 config file.

    @param themefile str: yaml theme file path.
    @param configfile str: i3 configuration file path.
    """
    with open(themefile) as tf:
        with open(configfile) as cf:
            return apply_theme_to_config(tf.read(), cf.read())

def listthemes(themeshome=None):
    if themeshome is None:
        themeshome = os.path.join(os.path.dirname(__file__), 'themes')
    if os.path.exists(themeshome):
        for e in os.listdir(themeshome):
            if os.path.isfile(e):
                pfrint (" - ", e)
    else:
        print("No available themes")

def console():
    import os
    theme = os.path.expanduser(sys.argv[1])
    cfile = os.path.expanduser(sys.argv[2])
    out = None
    if len(sys.argv)>3:
        out = os.path.expanduser(sys.argv[3])
    newconf = applytheme(theme, cfile)
    print(newconf)
    if out is not None:
        with open(out, "w") as f:
            f.write(newconf)

usage = """
i3stylepy apply -t/--theme [THEMENAME] -c/--config [CONFIGFILE] -o/--output [OUTPUTFILE]
i3style list
i3style extract -c/--config -o [THEMENAME]
"""

def console2():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subparsers")
    applyparser = subparsers.add_parser('apply')
    applyparser.add_argument('-t', '--theme',dest='theme')
    applyparser.add_argument('-c', '--config', dest='config')
    applyparser.add_argument('-o', '--output', dest="output")
    listparser = subparsers.add_parser('list')
    extractparser = subparsers.add_parser('extract')
    extractparser.add_argument('-c', '--config', dest='config')
    extractparser.add_argument('-o', '--output', dest='output')
    args = parser.parse_args()
    if args.subparsers == "list":
        listthemes()
    elif args.subparsers == "apply":
        theme = args.theme
        config = args.config
        output = args.output
        with open(output, "w") as outf:
            outf.write(applytheme(theme, config))
    elif args.subparsers == "extract":
        config = args.config
        output = args.output
        with open(config) as cf:
            config_s = cf.read()
            with open(output, "w") as fout:
                fout.write(theme_as_yaml(theme_from_config_string(config_s)))
    else:
        raise ValueError("Unknown subcommand.")

if __name__ == '__main__':
    console2()
