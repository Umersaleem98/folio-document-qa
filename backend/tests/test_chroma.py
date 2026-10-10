def test_real_chroma_persistence_owner_filter_and_delete(tmp_path):
    import chromadb
    from chromadb.config import Settings
    path=str(tmp_path/'chroma')
    config=Settings(anonymized_telemetry=False)
    client=chromadb.PersistentClient(path=path,settings=config)
    col=client.get_or_create_collection('test_documents',embedding_function=None,metadata={'hnsw:space':'cosine'})
    col.upsert(ids=['a','b'],embeddings=[[1.,0.,0.],[0.,1.,0.]],documents=['Owner A document text','Owner B private text'],
        metadatas=[{'owner_id':'a','document_id':'doc_a','page':1},{'owner_id':'b','document_id':'doc_b','page':2}])
    result=col.query(query_embeddings=[[1.,0.,0.]],n_results=1,
        where={'$and':[{'owner_id':'a'},{'document_id':{'$in':['doc_a']}}]},include=['documents','metadatas','distances'])
    assert result['ids']==[['a']]
    assert result['documents']==[['Owner A document text']]
    reopened=chromadb.PersistentClient(path=path,settings=config).get_collection('test_documents',embedding_function=None)
    assert reopened.count()==2
    reopened.delete(where={'document_id':'doc_a'})
    assert reopened.count()==1
    assert reopened.get()['ids']==['b']
