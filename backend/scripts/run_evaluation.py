"""
Recommender System Evaluation Runner

This script runs a comprehensive evaluation of the collaborative filtering recommender system
and generates a professional evaluation report suitable for presentations.
"""

import sys
import os
import json
import datetime
from pathlib import Path

# Add the parent directory to the path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.services.evaluation_service import RecommenderEvaluationService
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def format_evaluation_report(results: dict) -> str:
    """Format evaluation results into a professional report."""
    
    report = []
    report.append("=" * 80)
    report.append("🎬 MOVIE RECOMMENDER SYSTEM - EVALUATION REPORT")
    report.append("=" * 80)
    report.append(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Evaluation Framework: Collaborative Filtering Assessment")
    report.append("")
    
    # Dataset Summary
    if "evaluation_summary" in results:
        summary = results["evaluation_summary"]
        report.append("📊 DATASET OVERVIEW")
        report.append("-" * 40)
        report.append(f"Total Users:           {summary.get('total_users', 'N/A'):,}")
        report.append(f"Total Movies:          {summary.get('total_items', 'N/A'):,}")
        report.append(f"Training Ratings:      {summary.get('train_ratings', 'N/A'):,}")
        report.append(f"Test Ratings:          {summary.get('test_ratings', 'N/A'):,}")
        report.append("")
    
    # Accuracy Metrics
    if "accuracy_metrics" in results:
        accuracy = results["accuracy_metrics"]
        report.append("🎯 ACCURACY METRICS")
        report.append("-" * 40)
        report.append("These metrics measure how well the system predicts user ratings:")
        report.append("")
        
        mae = accuracy.get('MAE', 'N/A')
        rmse = accuracy.get('RMSE', 'N/A')
        
        report.append(f"Mean Absolute Error (MAE):     {mae}")
        report.append(f"Root Mean Square Error (RMSE): {rmse}")
        report.append("")
        
        # Interpretation
        if isinstance(mae, (int, float)):
            if mae < 0.7:
                mae_rating = "Excellent"
            elif mae < 1.0:
                mae_rating = "Good"
            elif mae < 1.3:
                mae_rating = "Fair"
            else:
                mae_rating = "Needs Improvement"
            report.append(f"📈 MAE Assessment: {mae_rating}")
        
        if isinstance(rmse, (int, float)):
            if rmse < 0.9:
                rmse_rating = "Excellent"
            elif rmse < 1.2:
                rmse_rating = "Good"
            elif rmse < 1.5:
                rmse_rating = "Fair"
            else:
                rmse_rating = "Needs Improvement"
            report.append(f"📈 RMSE Assessment: {rmse_rating}")
        report.append("")
    
    # Top-N Recommendation Metrics
    if "topn_metrics" in results:
        topn = results["topn_metrics"]
        report.append("🔝 TOP-N RECOMMENDATION METRICS")
        report.append("-" * 40)
        report.append("These metrics evaluate the quality of top-10 recommendations:")
        report.append("")
        
        hit_rate = topn.get('Hit_Rate', 'N/A')
        arhr = topn.get('ARHR', 'N/A')
        
        report.append(f"Hit Rate:                      {hit_rate}")
        report.append(f"Average Reciprocal Hit Rate:   {arhr}")
        report.append("")
        
        # Interpretation
        if isinstance(hit_rate, (int, float)):
            hit_rate_pct = hit_rate * 100
            report.append(f"📊 {hit_rate_pct:.1f}% of users received at least one relevant recommendation")
            
            if hit_rate > 0.6:
                hit_rating = "Excellent"
            elif hit_rate > 0.4:
                hit_rating = "Good"
            elif hit_rate > 0.2:
                hit_rating = "Fair"
            else:
                hit_rating = "Needs Improvement"
            report.append(f"📈 Hit Rate Assessment: {hit_rating}")
        
        if isinstance(arhr, (int, float)):
            report.append(f"📊 Average position of relevant items: {1/arhr:.1f}" if arhr > 0 else "📊 No relevant items found in top positions")
        report.append("")
    
    # Coverage Metrics
    if "coverage_metrics" in results:
        coverage = results["coverage_metrics"]
        report.append("📋 COVERAGE METRICS")
        report.append("-" * 40)
        report.append("These metrics measure the breadth of recommendations:")
        report.append("")
        
        catalog_coverage = coverage.get('Catalog_Coverage', 'N/A')
        user_coverage = coverage.get('User_Coverage', 'N/A')
        
        report.append(f"Catalog Coverage:              {catalog_coverage}")
        report.append(f"User Coverage:                 {user_coverage}")
        report.append("")
        
        if isinstance(catalog_coverage, (int, float)):
            catalog_pct = catalog_coverage * 100
            report.append(f"📊 {catalog_pct:.1f}% of available movies can be recommended")
        
        if isinstance(user_coverage, (int, float)):
            user_pct = user_coverage * 100
            report.append(f"📊 {user_pct:.1f}% of users can receive recommendations")
        report.append("")
    
    # Diversity Metric
    if "diversity_metric" in results:
        diversity = results["diversity_metric"].get('Diversity', 'N/A')
        report.append("🌈 DIVERSITY METRIC")
        report.append("-" * 40)
        report.append("This metric measures variety within recommendation lists:")
        report.append("")
        report.append(f"Intra-list Diversity:          {diversity}")
        report.append("")
        
        if isinstance(diversity, (int, float)):
            if diversity > 0.7:
                div_rating = "Excellent - High variety"
            elif diversity > 0.5:
                div_rating = "Good - Moderate variety"
            elif diversity > 0.3:
                div_rating = "Fair - Some variety"
            else:
                div_rating = "Low - Limited variety"
            report.append(f"📈 Diversity Assessment: {div_rating}")
        report.append("")
    
    # Novelty Metric
    if "novelty_metric" in results:
        novelty = results["novelty_metric"].get('Novelty', 'N/A')
        report.append("✨ NOVELTY METRIC")
        report.append("-" * 40)
        report.append("This metric measures how novel/surprising recommendations are:")
        report.append("")
        report.append(f"Mean Novelty Score:            {novelty}")
        report.append("")
        
        if isinstance(novelty, (int, float)):
            if novelty > 0.7:
                nov_rating = "High - Recommends lesser-known items"
            elif novelty > 0.5:
                nov_rating = "Moderate - Balanced popular/novel mix"
            elif novelty > 0.3:
                nov_rating = "Low-Moderate - Tends toward popular items"
            else:
                nov_rating = "Low - Focuses on popular items"
            report.append(f"📈 Novelty Assessment: {nov_rating}")
        report.append("")
    
    # Overall Assessment
    report.append("🏆 OVERALL SYSTEM ASSESSMENT")
    report.append("-" * 40)
    
    # Calculate overall score based on available metrics
    scores = []
    assessments = []
    
    if "accuracy_metrics" in results:
        mae = results["accuracy_metrics"].get('MAE')
        if isinstance(mae, (int, float)):
            if mae < 0.7:
                scores.append(4)
                assessments.append("Excellent accuracy")
            elif mae < 1.0:
                scores.append(3)
                assessments.append("Good accuracy")
            elif mae < 1.3:
                scores.append(2)
                assessments.append("Fair accuracy")
            else:
                scores.append(1)
                assessments.append("Accuracy needs improvement")
    
    if "topn_metrics" in results:
        hit_rate = results["topn_metrics"].get('Hit_Rate')
        if isinstance(hit_rate, (int, float)):
            if hit_rate > 0.6:
                scores.append(4)
                assessments.append("Excellent recommendation relevance")
            elif hit_rate > 0.4:
                scores.append(3)
                assessments.append("Good recommendation relevance")
            elif hit_rate > 0.2:
                scores.append(2)
                assessments.append("Fair recommendation relevance")
            else:
                scores.append(1)
                assessments.append("Recommendation relevance needs improvement")
    
    if "diversity_metric" in results:
        diversity = results["diversity_metric"].get('Diversity')
        if isinstance(diversity, (int, float)):
            if diversity > 0.5:
                scores.append(3)
                assessments.append("Good diversity")
            elif diversity > 0.3:
                scores.append(2)
                assessments.append("Moderate diversity")
            else:
                scores.append(1)
                assessments.append("Limited diversity")
    
    if scores:
        avg_score = sum(scores) / len(scores)
        if avg_score >= 3.5:
            overall_rating = "EXCELLENT"
            emoji = "🌟"
        elif avg_score >= 2.5:
            overall_rating = "GOOD"
            emoji = "👍"
        elif avg_score >= 1.5:
            overall_rating = "FAIR"
            emoji = "👌"
        else:
            overall_rating = "NEEDS IMPROVEMENT"
            emoji = "⚠️"
        
        report.append(f"{emoji} Overall Rating: {overall_rating}")
        report.append("")
        report.append("Key Strengths:")
        for assessment in assessments:
            report.append(f"  ✓ {assessment}")
    
    report.append("")
    report.append("📝 METHODOLOGY NOTE")
    report.append("-" * 40)
    report.append("This evaluation follows industry-standard metrics for collaborative")
    report.append("filtering recommender systems. The assessment is based on a")
    report.append("chronological train/test split to simulate real-world performance.")
    report.append("")
    report.append("Reference: https://medium.com/nerd-for-tech/evaluating-recommender-systems-590a7b87afa5")
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)


def save_results(results: dict, report: str):
    """Save evaluation results and report to files."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON results
    json_file = f"evaluation_results_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Save formatted report
    report_file = f"evaluation_report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Results saved to: {json_file}")
    logger.info(f"Report saved to: {report_file}")
    
    return json_file, report_file


def main():
    """Run the comprehensive evaluation."""
    logger.info("Starting recommender system evaluation...")
    
    try:
        # Initialize evaluation service
        eval_service = RecommenderEvaluationService()
        
        # Run evaluation
        results = eval_service.run_comprehensive_evaluation()
        
        if "error" in results:
            logger.error(f"Evaluation failed: {results['error']}")
            return
        
        # Format report
        report = format_evaluation_report(results)
        
        # Print report to console
        print("\n" + report)
        
        # Save results
        json_file, report_file = save_results(results, report)
        
        logger.info("Evaluation completed successfully!")
        logger.info(f"Files generated: {json_file}, {report_file}")
        
    except Exception as e:
        logger.error(f"Evaluation failed with error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
