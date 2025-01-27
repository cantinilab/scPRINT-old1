# niceumap

import scanpy as sc
import datamapplot
from anndata.experimental import concat_on_disk
from umap import UMAP
import os



name = "o2uniqsx"
# Assuming the data files are in the "./data/" directory
data_directory = "./data/"
file_list = os.listdir(data_directory)
## Filter out only the files with the 'h5ad' extension
h5ad_files = [file for file in file_list if file.endswith('.h5ad') and "step_0_predict_part" in file]
## Sort the files to maintain order
h5ad_files.sort()
## Update the list 'l' with the full paths of the 'h5ad' files
h5ad_files = [os.path.join(data_directory, file) for file in h5ad_files]

concat_on_disk(h5ad_files, data_directory+name+"_predict.h5ad", uns_merge="same", index_unique="_")
adata = sc.read_h5ad(data_directory + name + "_predict.h5ad")
# adata = adata[:100_000]
# sc.pp.neighbors(adata, use_rep="X", n_neighbors=15)
# sc.tl.louvain(adata, resolution=1.0, key_added="louvain_1.0")
# sc.tl.louvain(adata, resolution=0.5, key_added="louvain_0.5")
# sc.tl.louvain(adata, resolution=0.2, key_added="louvain_0.2")

fit = UMAP(n_neighbors=15, min_dist=0.1, spread=1.4, metric="cosine")
adata.obsm["X_umap"] = fit.fit_transform(adata.X)

adata.write(data_directory + name + "_predict.h5ad")
# fig, ax = datamapplot.create_plot(adata.obsm['X_umap'],
#                                adata.obs['conv_pred_cell_type_ontology_term_id'],
#                                darkmode=False,
#                                title="Predicted Cell Types")

# fig.savefig(data_directory+"step_0_predict_umap_celltype.png", bbox_inches="tight")
