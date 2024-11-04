from pathlib import Path

html_fpath = Path("index.html")
html_fpath = html_fpath.open("w", encoding="utf-8")


html_fpath.write("<table width=\"100%\" class=\"samples\">\n")
html_fpath.write("<tbody>\n")
html_fpath.write("\t<tr>\n")
html_fpath.write("\t\t<th>Chunk Size</th>\n")
html_fpath.write("\t\t<th>Input speech</th>\n")
html_fpath.write("\t\t<th>Base</th>\n")
html_fpath.write("\t\t<th>Lite</th>\n")
html_fpath.write("\t</tr>\n")
for chunk_size in [20, 40, 80, 160, 240, 320]:
    html_fpath.write("\t<tr>\n")
    html_fpath.write("\t\t<td rowspan=\"3\">"+str(chunk_size)+"ms</td>\n")
    for sample in ["arctic_a0010", "arctic_a0011", "arctic_a0012"]:
        for model in ["input", "base", "lite"]:
            if model == "input":
                audio_fpath = f"wav/input/{sample}.wav"
            else:
                audio_fpath = f"wav/output/{model}/cs_{chunk_size}/{sample}.wav"
            html_fpath.write("\t\t<td>\n")
            html_fpath.write("\t\t\t<audio controls=\"\">\n")
            html_fpath.write("\t\t\t\t<source src=\"" + audio_fpath + "\" type=\"audio/wav\">Your browser does not support the audio tag.</source>\n")
            html_fpath.write("\t\t\t</audio>\n")
            html_fpath.write("\t\t<td>\n")
        
    html_fpath.write("\t\t<td>\n")
    html_fpath.write("\t</tr>\n")

html_fpath.write("</tbody>\n")
html_fpath.write("</table>\n")

