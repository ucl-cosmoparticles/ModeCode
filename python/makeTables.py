import os, batchJobArgs, ResultObjs


Opts = batchJobArgs.batchArgs('Make pdf tables from latex generated from getdist outputs', importance=True, converge=True)
Opts.parser.add_argument('latex_filename')
Opts.parser.add_argument('--bestfitonly', action='store_true')
Opts.parser.add_argument('--bestfit', action='store_true', default=True)

# this is just for the latex labelsm set None to use those in chain .paramnames
Opts.parser.add_argument('--paramNameFile', default='clik_latex.paramnames')
Opts.parser.add_argument('--blockEndParams', default=None)
Opts.parser.add_argument('--columns', type=int, nargs=1, default=3)
Opts.parser.add_argument('--compare', nargs='+', default=None)
Opts.parser.add_argument('--portrait', action='store_true')
Opts.parser.add_argument('--titles', default=None)  # for compare plots
Opts.parser.add_argument('--forpaper', action='store_true')


(batch, args) = Opts.parseForBatch()

if args.blockEndParams is not None: args.blockEndParams = args.blockEndParams.split(';')
outfile = args.latex_filename
if outfile.find('.') < 0: outfile += '.tex'

lines = []
if not args.forpaper:
    lines.append('\\documentclass[10pt]{article}')
    lines.append('\\usepackage{fullpage}')
    lines.append('\\usepackage[pdftex]{hyperref}')
    if args.portrait: lines.append('\\usepackage[paperheight=15in,margin=0.8in]{geometry}')
    else: lines.append('\\usepackage[landscape,margin=0.8in]{geometry}')

    lines.append('\\renewcommand{\\arraystretch}{1.5}')
    lines.append('\\begin{document}')
    lines.append('\\tableofcontents')

def texEscapeText(string):
    return string.replace('_', '{\\textunderscore}')

def paramResultTable(jobItem):
    tableLines = []
    caption = ''
    jobItem.loadJobItemResults(paramNameFile=args.paramNameFile, bestfit=args.bestfit, bestfitonly=args.bestfitonly)
    bf = jobItem.result_bestfit
    if not bf is None:
        caption += ' Best-fit $\\chi^2_{\\rm eff} = ' + ('%.2f' % (jobItem.result_bestfit.logLike * 2)) + '$'
    if args.bestfitonly:
        tableLines += ResultObjs.resultTable(args.columns, [bf], blockEndParams=args.blockEndParams).lines
    else:
        if not jobItem.result_converge is None: caption += '; R-1 =' + jobItem.result_converge.worstR()
        if not jobItem.result_marge is None: tableLines += ResultObjs.resultTable(args.columns, [jobItem.result_marge], blockEndParams=args.blockEndParams).lines
    tableLines.append('')
    if not args.forpaper: tableLines.append(caption)
    if not bf is None and not args.forpaper:
        tableLines.append('')
        tableLines.append('$\chi^2_{\\rm eff}$:')
        for kind, vals in bf.sortedChiSquareds():
            tableLines.append(kind + ' - ')
            for (name, chisq) in vals:
                tableLines.append('  ' + texEscapeText(name) + ': ' + ('%.2f' % chisq) + ' ')
    return tableLines

def compareTable(jobItems, titles=None):
    for jobItem in jobItems:
        jobItem.loadJobItemResults(paramNameFile=args.paramNameFile, bestfit=args.bestfit, bestfitonly=args.bestfitonly)
        print jobItem.name
    if titles is None: titles = [jobItem.datatag for jobItem in jobItems if jobItem.result_marge is not None]
    else: titles = titles.split(';')
    return ResultObjs.resultTable(1, [jobItem.result_marge for jobItem in jobItems if jobItem.result_marge is not None],
                                   titles=titles, blockEndParams=args.blockEndParams).lines

def filterBatchData(batch, datatags):
    items = []
    for tag in datatags:
        items += [jobItem for jobItem in batch if jobItem.datatag == tag]
    return items

items = dict()
for jobItem in Opts.filteredBatchItems():
    if not jobItem.paramtag in items: items[jobItem.paramtag] = []
    items[jobItem.paramtag].append(jobItem)
items = sorted(items.iteritems())

for paramtag, parambatch in items:
    if not args.forpaper: lines.append('\\section{ ' + texEscapeText("+".join(parambatch[0].param_set)) + '}')
    if not args.compare is None:
        compares = filterBatchData(parambatch, args.compare)
        if len(compares) > 0:
            lines += compareTable(compares, args.titles)
        else: print 'no matches for compare'
    else:
        for jobItem in parambatch:
            if args.converge == 0 or jobItem.hasConvergeBetterThan(args.converge):
                if not args.forpaper: lines.append('\\subsection{ ' + texEscapeText(jobItem.name) + '}')
                tableLines = paramResultTable(jobItem)
                ResultObjs.textFile(tableLines).write(jobItem.distRoot + '.tex')
                lines += tableLines
    if not args.forpaper: lines.append('\\newpage')

if not args.forpaper: lines.append('\\end{document}')

ResultObjs.textFile(lines).write(outfile)

if not args.forpaper:
    print 'Now converting to PDF...'
    os.system('pdflatex ' + outfile)
    # #again to get table of contents
    os.system('pdflatex ' + outfile)

