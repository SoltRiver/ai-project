/**
 * Lighthouse CI 設定ファイル
 *
 * /ui_test ワークフローの Phase 5 で使用される技術的品質チェックの設定。
 * FastAPI サーバーを専用ポート(8765)で自動起動し、主要ページの品質を計測する。
 *
 * 環境変数:
 *   - TEST_MODE=true: テストモードで起動（外部APIコールを抑制）
 *   - LIGHTHOUSE_CI=true: Lighthouse CI モードで起動（重い処理をスキップ）
 *
 * ローカル実行:
 *   npm run lhci
 *
 * CI環境での実行:
 *   TEST_MODE=true LIGHTHOUSE_CI=true npm run lhci
 */
module.exports = {
  ci: {
    collect: {
      // FastAPI サーバーを Lighthouse CI 専用ポートで起動
      // TEST_MODE / LIGHTHOUSE_CI 環境変数で外部API・AI処理を抑制
      startServerCommand:
        'python -m uvicorn fastapi_app:app --host 127.0.0.1 --port 8765',
      // サーバー起動完了を検知するパターン
      startServerReadyPattern: 'Uvicorn running on',
      // 計測対象URL（外部API依存が低く安定して測定可能なページ）
      // 注意: /stocks/7203 等のAPIヘビーなページは初期段階では除外
      url: [
        'http://127.0.0.1:8765/stocks',
        'http://127.0.0.1:8765/indices',
        'http://127.0.0.1:8765/glossary',
        'http://127.0.0.1:8765/candle-patterns',
      ],
      // 計測回数（3回の中央値を採用し、ばらつきを抑える）
      numberOfRuns: 3,
      settings: {
        // デスクトッププリセット（モバイル計測はThrottlingが厳しいため初期はデスクトップ）
        preset: 'desktop',
        // Chrome起動オプション（CI環境向け）
        chromeFlags: '--no-sandbox --disable-dev-shm-usage',
      },
    },
    assert: {
      assertions: {
        // ========================================
        // カテゴリスコア（0.0〜1.0）
        // 初期段階は全て warn レベル（CIをブロックしない）
        // 安定してきたら error に昇格して厳格化する
        // ========================================

        // Performance: 初期閾値 0.6（画像最適化やキャッシュ未導入のため低めに設定）
        'categories:performance': ['warn', { minScore: 0.6 }],
        // Accessibility: 閾値 0.85（WCAG AA 準拠を目指す）
        'categories:accessibility': ['warn', { minScore: 0.85 }],
        // Best Practices: 閾値 0.8（HTTPS未使用等のローカル特有の減点あり）
        'categories:best-practices': ['warn', { minScore: 0.8 }],
        // SEO: 閾値 0.7（メタタグ未整備のため低めに設定）
        'categories:seo': ['warn', { minScore: 0.7 }],

        // ========================================
        // 個別メトリクス（ミリ秒 / 数値）
        // ========================================

        // First Contentful Paint: 最初のコンテンツ描画まで 3000ms 以内
        'first-contentful-paint': ['warn', { maxNumericValue: 3000 }],
        // Largest Contentful Paint: 最大コンテンツ描画まで 4000ms 以内
        'largest-contentful-paint': ['warn', { maxNumericValue: 4000 }],
        // Cumulative Layout Shift: レイアウトずれの累積値 0.1 以下
        'cumulative-layout-shift': ['warn', { maxNumericValue: 0.1 }],
      },
    },
    upload: {
      // 結果を一時的な公開ストレージにアップロード（URL共有で結果閲覧可能）
      target: 'temporary-public-storage',
    },
  },
};
