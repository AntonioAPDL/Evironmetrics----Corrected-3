#!/usr/bin/env Rscript
# Bounded replay of archived display summaries; never reads fitted-model caches.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("Expected root and scratch output directory")
root <- normalizePath(args[[1]], mustWork = TRUE)
out <- normalizePath(args[[2]], mustWork = TRUE)
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(patchwork))
source(file.path(root, "artifacts/comment1_figure_revision/renderer_sources/R/unified/post_publication_figures.R"), local = TRUE)
cfg <- yaml::read_yaml(file.path(root, "config/predictive_synthesis_figures.yaml"))
# Start with the archived publication style, then apply every intended override.
archived <- yaml::read_yaml(file.path(root, cfg$derived_from))
style <- post_publication_merge_lists(archived, cfg$style)
style["y_limits"] <- list(NULL)
style["y_limits_by_cutoff"] <- list(list())
origins <- c("20210123", "20211112", "20211221", "20220511", "20221225")
plots <- list()
audit <- list()
for (o in origins) {
  source_dir <- file.path(root, "artifacts/five_cutoff_main_model_synthesis", paste0(o, "_exal_m_t1"))
  display_dir <- file.path(root, "artifacts/predictive_synthesis_figures/inputs", o)
  q <- read.csv(file.path(source_dir, "exdqlm_multivar_synth_keep_focus_render_numeric_contract.csv"), check.names = FALSE)
  draws <- read.csv(file.path(source_dir, "exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv"), check.names = FALSE)
  draws <- draws[draws$sample_index %in% cfg$selected_sample_indices, , drop = FALSE]
  source_long <- function(filename, provider) {
    d <- read.csv(file.path(display_dir, filename), check.names = FALSE)
    do.call(rbind, lapply(names(d)[-1L], function(member) data.frame(date = as.Date(d[[1]]), provider = provider, member = member, value = d[[member]], stringsAsFactors = FALSE)))
  }
  ensembles <- rbind(source_long("glofas_post_adapter.csv", "GloFAS"), source_long("nws_post_adapter.csv", "NWM"))
  ret <- read.csv(file.path(display_dir, "retros_post_adapter.csv"), check.names = FALSE)
  retrospective <- rbind(data.frame(date = as.Date(ret$Date), provider = "GloFAS", source = "GloFAS", value = ret$GloFAS), data.frame(date = as.Date(ret$Date), provider = "NWM", source = "NWS3.0", value = ret[["NWS3.0"]]))
  # The frozen function writes two obligatory scratch files, never published paths.
  result <- post_publication_render_focus_posterior_plot("exdqlm_multivar_synth_keep", q, draws,
    file.path(out, paste0("scratch_", o, ".png")), file.path(out, paste0("scratch_", o, ".pdf")),
    style, ensemble_df = ensembles, retrospective_df = retrospective)
  built <- ggplot2::ggplot_build(result$plot)
  ribbon_index <- which(vapply(result$plot$layers, function(layer) inherits(layer$geom, "GeomRibbon"), logical(1)))
  mean_index <- which(vapply(result$plot$layers, function(layer) identical(rlang::get_expr(layer$mapping$y), quote(.data[["model_mean"]])), logical(1)))
  sample_index <- which(vapply(result$plot$layers, function(layer) identical(rlang::get_expr(layer$mapping$group), quote(interaction(segment, sample_index))), logical(1)))
  stopifnot(length(ribbon_index) == 1L, length(mean_index) == 1L, length(sample_index) == 1L)
  stopifnot(isTRUE(all.equal(built$data[[ribbon_index]]$ymin, q$interval_low, tolerance = 1e-14)),
            isTRUE(all.equal(built$data[[ribbon_index]]$ymax, q$interval_high, tolerance = 1e-14)),
            isTRUE(all.equal(built$data[[mean_index]]$y, q$model_mean, tolerance = 1e-14)),
            nrow(built$data[[sample_index]]) == 470L, length(unique(built$data[[sample_index]]$group)) == 20L)
  origin <- as.Date(o, format = "%Y%m%d")
  p <- result$plot + coord_cartesian(ylim = unlist(cfg$primary_y_limits), expand = FALSE) +
    labs(title = sprintf("exAL-M-T1: %s", format(origin, "%B %d, %Y")), subtitle = NULL, caption = NULL) +
    theme(text = element_text(family = cfg$font_family), legend.text = element_text(size = 8), axis.text = element_text(size = 8), axis.title = element_text(size = 9),
      legend.key.width = grid::unit(21, "pt"), plot.title = element_text(size = 10.5), plot.margin = margin(6, 6, 3, 3))
  # These independently styled guide labels do not alter legend keys or data.
  rename_trace <- function(x) ifelse(x == "Predictive sample paths", "Predictive sample traces", x)
  for (a in c("colour", "linetype", "shape")) {
    sc <- p$scales$get_scales(a)
    sc$labels <- rename_trace
  }
  if (o == "20220511") {
    detail <- p + coord_cartesian(ylim = unlist(cfg$may_detail_y_limits), expand = FALSE) +
      labs(title = "May detail: 0 to 1.3", x = NULL, y = NULL) +
      scale_y_continuous(breaks = c(0, .6, 1.2)) +
      theme(legend.position = "none", axis.text = element_text(size = 6.5),
        plot.title = element_text(size = 7.5), panel.background = element_rect(fill = "white", colour = "#687782"),
        plot.background = element_rect(fill = "white", colour = "#687782"), plot.margin = margin(3, 3, 3, 3))
    p <- p + inset_element(detail, left = .28, bottom = .27, right = .985, top = .70, align_to = "panel")
  }
  plots[[o]] <- p
  audit[[o]] <- list(summary_rows = nrow(q), history_rows = sum(q$segment == "history"), forecast_rows = sum(q$segment == "forecast"),
    sample_rows = nrow(draws), selected_sample_indices = sort(unique(draws$sample_index)),
    sample_groups = length(unique(interaction(draws$segment, draws$sample_index))),
    glofas_rows = sum(ensembles$provider == "GloFAS"), nws_rows = sum(ensembles$provider == "NWM"), retrospective_rows = nrow(retrospective),
    built_mean_and_exact_interval_verified = TRUE, built_sample_rows = nrow(built$data[[sample_index]]), built_sample_groups = length(unique(built$data[[sample_index]]$group)),
    mean_source = "model_mean", lower_source = "interval_low", upper_source = "interval_high", interval_probabilities = c(.025, .975), scale = "log1p_cms")
}
export <- function(p, name, width, height) {
  path <- file.path(out, name)
  grDevices::cairo_pdf(path, width = width, height = height, family = cfg$font_family, bg = "white", onefile = TRUE)
  print(p)
  invisible(dev.off())
}
export(plots[["20221225"]], "predictive_synthesis_2022_12_25.pdf", cfg$single_width_in, cfg$single_height_in)
export((plots[["20210123"]] / plots[["20211112"]]) + plot_layout(guides = "collect") & theme(legend.position = "bottom", legend.box = "vertical", legend.direction = "horizontal"), "compact_forecasts_2021_early.pdf", cfg$pair_width_in, cfg$pair_height_in)
export((plots[["20211221"]] / plots[["20220511"]]) + plot_layout(guides = "collect") & theme(legend.position = "bottom", legend.box = "vertical", legend.direction = "horizontal"), "compact_forecasts_2021_2022.pdf", cfg$pair_width_in, cfg$pair_height_in)
env <- list(R = as.character(getRversion()), ggplot2 = as.character(packageVersion("ggplot2")), patchwork = as.character(packageVersion("patchwork")), yaml = as.character(packageVersion("yaml")), jsonlite = as.character(packageVersion("jsonlite")), locale = Sys.getlocale(), device = "grDevices::cairo_pdf", font_family = cfg$font_family, graphics_libraries = as.list(grDevices::grSoftVersion()))
jsonlite::write_json(list(environment = env, layers = audit), file.path(out, "render_audit.json"), pretty = TRUE, auto_unbox = TRUE, digits = 17)
